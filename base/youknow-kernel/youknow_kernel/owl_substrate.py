"""
OWL Domain Ontology Writer and Carton Mirror

The dual-substrate pattern:
1. Entities go INTO OWL (source of truth for logic)
2. OWL entities are MIRRORED to Carton (search/agent layer)
3. Pellet runs on OWL for reasoning
4. Carton uses mirror for ChromaRAG/Neo4j

This module provides:
- OWLWriter: Writes entities to OWL files
- CartonMirror: Syncs OWL changes to Carton
- DualSubstrate: Unified interface for both
"""

import os
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET
from xml.dom import minidom

# Carton queue dir - write directly, no import needed
# Daemon processes these files with ZERO YOUKNOW involvement
import json
import uuid

def _get_carton_queue_dir() -> str:
    """Get carton queue directory path (same as daemon reads from)."""
    heaven_data = os.getenv('HEAVEN_DATA_DIR', '/tmp/heaven_data')
    queue_dir = os.path.join(heaven_data, 'carton_queue')
    os.makedirs(queue_dir, exist_ok=True)
    return queue_dir


def _normalize_concept_name(name: str) -> str:
    """Normalize to Title_Case_With_Underscores (matches Carton convention)."""
    return name.replace("_", " ").title().replace(" ", "_")


@dataclass
class OWLEntity:
    """An entity to be written to OWL."""
    
    name: str
    description: str
    is_a: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    
    # PIO metadata
    is_hyperedge: bool = False
    isomorphism_members: List[str] = field(default_factory=list)
    
    # EMR metadata
    emr_state: str = "embodies"  # embodies, manifests, reifies
    ses_layer: int = 0
    
    def to_owl_class(self, namespace: str = "http://sanctuary.ai/domain#") -> str:
        """Generate OWL class XML for this entity."""
        
        uarl_ns = "http://sanctuary.ai/uarl#"
        
        # Build subclass relationships (is_a)
        subclass_of = ""
        for parent in self.is_a:
            subclass_of += f'        <rdfs:subClassOf rdf:resource="{namespace}{parent}"/>\n'
        
        # Build description
        desc = self.description.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Build ALL relationships as restrictions/assertions
        relationships_xml = ""
        
        for rel_type, targets in self.relationships.items():
            for target in targets:
                # Map relationship types to OWL
                if rel_type == "part_of":
                    relationships_xml += f'''        <rdfs:subClassOf>
            <owl:Restriction>
                <owl:onProperty rdf:resource="{uarl_ns}partOf"/>
                <owl:someValuesFrom rdf:resource="{namespace}{target}"/>
            </owl:Restriction>
        </rdfs:subClassOf>
'''
                elif rel_type == "has_part":
                    relationships_xml += f'''        <rdfs:subClassOf>
            <owl:Restriction>
                <owl:onProperty rdf:resource="{uarl_ns}hasPart"/>
                <owl:someValuesFrom rdf:resource="{namespace}{target}"/>
            </owl:Restriction>
        </rdfs:subClassOf>
'''
                elif rel_type == "compareFrom":
                    relationships_xml += f'        <uarl:compareFrom rdf:resource="{namespace}{target}"/>\n'
                elif rel_type == "mapsTo":
                    relationships_xml += f'        <uarl:mapsTo rdf:resource="{namespace}{target}"/>\n'
                elif rel_type == "analogicalPattern":
                    relationships_xml += f'        <uarl:analogicalPattern rdf:resource="{namespace}{target}"/>\n'
                elif rel_type == "intuition":
                    relationships_xml += f'        <uarl:intuition rdf:resource="{namespace}{target}"/>\n'
                elif rel_type == "embodies":
                    relationships_xml += f'        <uarl:embodies rdf:resource="{namespace}{target}"/>\n'
                elif rel_type == "manifests":
                    relationships_xml += f'        <uarl:manifests rdf:resource="{namespace}{target}"/>\n'
                elif rel_type == "reifies":
                    relationships_xml += f'        <uarl:reifies rdf:resource="{namespace}{target}"/>\n'
                elif rel_type == "produces":
                    relationships_xml += f'        <uarl:produces rdf:resource="{namespace}{target}"/>\n'
                elif rel_type == "programs":
                    relationships_xml += f'        <uarl:programs rdf:resource="{namespace}{target}"/>\n'
                elif rel_type == "depends_on":
                    relationships_xml += f'        <uarl:dependsOn rdf:resource="{namespace}{target}"/>\n'
                elif rel_type == "relates_to":
                    relationships_xml += f'        <uarl:relatesTo rdf:resource="{namespace}{target}"/>\n'
                else:
                    # Generic relationship
                    relationships_xml += f'        <uarl:{rel_type} rdf:resource="{namespace}{target}"/>\n'
        
        # Build property annotations
        props = ""
        for prop_name, prop_value in self.properties.items():
            # Escape value
            val = str(prop_value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            props += f'        <uarl:{prop_name}>{val}</uarl:{prop_name}>\n'
        
        # PIO hyperedge annotation
        pio_annotation = ""
        if self.is_hyperedge:
            members = ", ".join(self.isomorphism_members)
            pio_annotation += f'        <uarl:isHyperedge rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">true</uarl:isHyperedge>\n'
            for member in self.isomorphism_members:
                pio_annotation += f'        <uarl:hyperedgeMember rdf:resource="{namespace}{member}"/>\n'
        
        # EMR state annotation
        emr_annotation = f'        <uarl:emrState>{self.emr_state}</uarl:emrState>\n'
        emr_annotation += f'        <uarl:sesLayer rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">{self.ses_layer}</uarl:sesLayer>\n'
        
        return f'''
    <owl:Class rdf:about="{namespace}{self.name}">
        <rdfs:label>{self.name}</rdfs:label>
        <rdfs:comment>{desc}</rdfs:comment>
{subclass_of}{relationships_xml}{props}{pio_annotation}{emr_annotation}    </owl:Class>
'''


class OWLWriter:
    """Writes entities to OWL domain ontology files."""
    
    def __init__(
        self,
        owl_dir: str = "/tmp/youknow_owl",
        domain_file: str = "domain.owl",
        namespace: str = "http://sanctuary.ai/domain#"
    ):
        self.owl_dir = owl_dir
        self.domain_file = os.path.join(owl_dir, domain_file)
        self.namespace = namespace
        
        # Ensure domain file exists
        if not os.path.exists(self.domain_file):
            self._create_domain_ontology()
    
    def _create_domain_ontology(self):
        """Create the initial domain ontology file."""
        template = f'''<?xml version="1.0"?>
<rdf:RDF xmlns="{self.namespace}"
     xml:base="{self.namespace[:-1]}"
     xmlns:owl="http://www.w3.org/2002/07/owl#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:xml="http://www.w3.org/XML/1998/namespace"
     xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
     xmlns:uarl="http://sanctuary.ai/uarl#">
    
    <owl:Ontology rdf:about="{self.namespace[:-1]}">
        <rdfs:label>Domain Ontology</rdfs:label>
        <rdfs:comment>
Generated domain ontology. Entities created via PIO/YOUKNOW are written here.
Mirrored to Carton for search/agent access.
        </rdfs:comment>
        <owl:imports rdf:resource="http://sanctuary.ai/uarl"/>
        <owl:versionInfo>Auto-generated {datetime.now().isoformat()}</owl:versionInfo>
    </owl:Ontology>
    
    <!-- EMR State Property -->
    <owl:DatatypeProperty rdf:about="http://sanctuary.ai/uarl#emrState">
        <rdfs:label>EMR State</rdfs:label>
        <rdfs:comment>Current EMR state: embodies, manifests, or reifies</rdfs:comment>
    </owl:DatatypeProperty>
    
    <owl:DatatypeProperty rdf:about="http://sanctuary.ai/uarl#sesLayer">
        <rdfs:label>SES Layer</rdfs:label>
        <rdfs:comment>Current SES validation layer (0-6)</rdfs:comment>
    </owl:DatatypeProperty>

    <!-- ENTITIES GO HERE -->

</rdf:RDF>
'''
        os.makedirs(self.owl_dir, exist_ok=True)
        with open(self.domain_file, 'w') as f:
            f.write(template)
    
    def write_entity(self, entity: OWLEntity) -> bool:
        """Write an entity to the domain ontology."""
        try:
            # Read current file
            with open(self.domain_file, 'r') as f:
                content = f.read()
            
            # Generate OWL class
            owl_class = entity.to_owl_class(self.namespace)
            
            # Insert before closing </rdf:RDF>
            insert_point = content.rfind("</rdf:RDF>")
            if insert_point == -1:
                return False
            
            new_content = content[:insert_point] + owl_class + "\n" + content[insert_point:]
            
            # Write back
            with open(self.domain_file, 'w') as f:
                f.write(new_content)
            
            return True
            
        except Exception as e:
            print(f"Error writing entity to OWL: {e}")
            return False
    
    def write_entities(self, entities: List[OWLEntity]) -> int:
        """Write multiple entities. Returns count of successful writes."""
        success = 0
        for entity in entities:
            if self.write_entity(entity):
                success += 1
        return success
    
    def entity_exists(self, name: str) -> bool:
        """Check if entity already exists in OWL."""
        try:
            with open(self.domain_file, 'r') as f:
                content = f.read()
            return f'rdf:about="{self.namespace}{name}"' in content
        except:
            return False


class CartonMirror:
    """Mirrors OWL entities to Carton queue (Neo4j + ChromaRAG).

    Writes JSON directly to carton_queue/. Daemon processes with ZERO
    YOUKNOW involvement — YOUKNOW already validated before we get here.
    """

    def __init__(self):
        self.mirrored: List[str] = []

    def mirror_entity(self, entity: OWLEntity) -> str:
        """Mirror an OWL entity to Carton queue (direct JSON write).

        Does NOT call add_concept_tool_func — that would re-trigger YOUKNOW.
        Instead writes the same JSON format the daemon expects.
        """
        try:
            # Build relationships for Carton
            relationships = []

            for parent in entity.is_a:
                relationships.append({
                    "relationship": "is_a",
                    "related": [parent]
                })

            # Add all other relationships from entity
            for rel_type, targets in entity.relationships.items():
                relationships.append({
                    "relationship": rel_type,
                    "related": targets
                })

            # Add PIO hyperedge relationship
            if entity.is_hyperedge and entity.isomorphism_members:
                relationships.append({
                    "relationship": "has_part",
                    "related": entity.isomorphism_members
                })

            # Add EMR state as tag
            relationships.append({
                "relationship": "has_tag",
                "related": [f"EMR_{entity.emr_state}"]
            })

            # Normalize name + relationship targets to Title_Case_With_Underscores
            normalized_name = _normalize_concept_name(entity.name)
            for rel in relationships:
                rel["related"] = [_normalize_concept_name(r) for r in rel["related"]]

            # Write directly to carton queue (same format daemon expects)
            queue_dir = _get_carton_queue_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            queue_file = os.path.join(queue_dir, f"{timestamp}_{unique_id}_concept.json")

            queue_data = {
                "raw_concept": True,
                "concept_name": normalized_name,
                "description": entity.description,
                "relationships": relationships,
                "desc_update_mode": "append",
                "hide_youknow": True,  # Already validated by YOUKNOW compiler
                "is_soup": False,  # Only valid chains reach DualSubstrate
                "soup_reason": None,
                "source": "youknow_dual_substrate",
            }

            with open(queue_file, 'w') as f:
                json.dump(queue_data, f, indent=2)

            self.mirrored.append(entity.name)
            return f"Queued {entity.name} to carton"

        except Exception as e:
            return f"Mirror error: {e}"
    
    def mirror_all(self, entities: List[OWLEntity]) -> List[str]:
        """Mirror multiple entities to Carton."""
        results = []
        for entity in entities:
            results.append(self.mirror_entity(entity))
        return results


class DualSubstrate:
    """Unified interface for OWL + Carton dual substrate.
    
    Write once → Both substrates updated.
    """
    
    def __init__(
        self,
        owl_dir: str = "/tmp/youknow_owl",
        domain_file: str = "domain.owl"
    ):
        self.owl = OWLWriter(owl_dir, domain_file)
        self.carton = CartonMirror()
    
    def add_entity(self, entity: OWLEntity) -> Dict[str, Any]:
        """Add entity to both OWL and Carton.
        
        Returns: { owl_success, carton_result }
        """
        # Write to OWL first (source of truth)
        owl_success = self.owl.write_entity(entity)
        
        # Mirror to Carton
        carton_result = self.carton.mirror_entity(entity) if owl_success else "Skipped (OWL failed)"
        
        return {
            "entity": entity.name,
            "owl_success": owl_success,
            "carton_result": carton_result
        }
    
    def add_entities(self, entities: List[OWLEntity]) -> List[Dict[str, Any]]:
        """Add multiple entities to both substrates."""
        return [self.add_entity(e) for e in entities]
    
    def from_pio_entity(self, pio_entity) -> OWLEntity:
        """Convert a PIOEntity to OWLEntity for writing."""
        return OWLEntity(
            name=pio_entity.name,
            description=pio_entity.description,
            is_a=pio_entity.is_a,
            is_hyperedge=pio_entity.is_hyperedge,
            isomorphism_members=list(pio_entity.isomorphisms.keys()) if hasattr(pio_entity, 'isomorphisms') else []
        )


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=== DUAL SUBSTRATE: OWL + CARTON ===")
    print()
    
    # Create dual substrate
    dual = DualSubstrate()
    
    # Create entities from PIO discovery
    entities = [
        OWLEntity(
            name="Patchy_Dog_Pirate_Bridge",
            description="Hyperedge connecting Dog to Pirate via Patchy (eye-patch)",
            is_a=["Eye_Patch_Accessory", "Analogical_Bridge"],
            is_hyperedge=True,
            isomorphism_members=["Dog", "Patchy", "Pirate"],
            emr_state="reifies",
            ses_layer=2
        ),
        OWLEntity(
            name="Patchy",
            description="Bridge concept: a patchy appearance that connects to pirate accessories",
            is_a=["Bridge_Concept", "Visual_Attribute"],
            emr_state="manifests",
            ses_layer=1
        ),
        OWLEntity(
            name="Eye_Patch_Accessory",
            description="Pattern: accessories that cover one eye, associated with pirates",
            is_a=["Pirate_Accessory", "Analogical_Pattern"],
            emr_state="reifies",
            ses_layer=3
        )
    ]
    
    print("Adding entities to dual substrate...")
    print()
    
    for entity in entities:
        result = dual.add_entity(entity)
        print(f"Entity: {result['entity']}")
        print(f"  OWL: {'✓' if result['owl_success'] else '✗'}")
        print(f"  Carton: {result['carton_result'][:50]}...")
        print()
    
    print(f"Domain ontology: {dual.owl.domain_file}")
