# Context Alignment Utils - Roadmap to MVP

## Critical Gap Identified: Missing File Dependencies

### The Problem

Our hybrid dependency analysis system currently has a **blind spot** that prevents it from being production-ready. We have identified that while our system captures:

1. ✅ **Structural Dependencies** (Neo4j): Function signatures, parameter types, class hierarchies
2. ✅ **Relational Dependencies** (Isaac's analyzer): Cross-file Python function/class calls

We are **completely missing**:

3. ❌ **File Dependencies**: Runtime file access patterns that are critical for complete code understanding

### Concrete Example of the Gap

```python
def setup_agent(config_path: str, template_name: str):
    """
    What our system currently captures:
    - Function signature: setup_agent(config_path: str, template_name: str)
    - Parameter types: str, str
    
    What we MISS (and MUST capture):
    - This function actually opens "brain_config.json" 
    - This function loads "templates/agent_prompt.jinja2"
    - This function reads environment variables from ".env"
    - This function imports data from "training_data.csv"
    """
    with open(config_path) as f:                    # File dependency: UNKNOWN
        config = json.load(f)
        
    template = env.get_template(template_name)      # Template dependency: UNKNOWN  
    data = pd.read_csv("training_data.csv")        # Data dependency: UNKNOWN
    api_key = os.getenv("OPENAI_API_KEY")          # Env dependency: UNKNOWN
```

### Why This Matters for Anti-Hallucination

When an AI agent tries to modify `setup_agent()`, it needs to know:
- **Structural**: Function signature and parameters ✅
- **Relational**: What other Python functions this calls ✅  
- **File Dependencies**: What config files, templates, and data this function depends on ❌

**Without file dependencies, the AI will:**
- Modify functions without understanding their data requirements
- Break configurations by not knowing which files are critical
- Make changes that fail at runtime due to missing file context
- Hallucinate about file structures and data formats

### Required Implementation: File Dependency Detection

We must enhance Isaac's dependency analyzer to detect and capture:

#### 1. Configuration Files
```python
# Detect these patterns:
json.load(open("config.json"))
yaml.safe_load(open("settings.yaml"))  
configparser.read("app.ini")
dotenv.load_dotenv(".env")
```

#### 2. Template Files  
```python
# Detect these patterns:
env.get_template("template.html")
Template("prompt.jinja2")
render_template("email.txt")
```

#### 3. Data Files
```python
# Detect these patterns:
pd.read_csv("data.csv")
np.load("weights.npy")
with open("input.txt") as f:
Image.open("logo.png")
```

#### 4. Dynamic File Paths
```python
# Detect these patterns:
os.path.join("configs", filename)
f"{base_path}/config.json"
Path("data") / "file.csv"
```

#### 5. Environment Variables
```python
# Detect these patterns:
os.getenv("CONFIG_PATH")
os.environ["API_KEY"]
```

### Implementation Strategy

#### Phase 1: Extend AST Visitor (Priority: Critical)
Add new visitor methods to `DependencyCollector`:
- `visit_Call()` enhancement to detect file operation patterns
- `visit_Constant()` to capture string literals that look like file paths
- `visit_JoinedStr()` to handle f-string file paths

#### Phase 2: File Path Pattern Recognition (Priority: Critical)  
Create pattern detection for:
- File extensions: `.json`, `.yaml`, `.csv`, `.txt`, `.html`, `.jinja2`, etc.
- File operation functions: `open()`, `load()`, `read_csv()`, etc.
- Path construction: `os.path.join()`, `Path()`, f-strings with `/`

#### Phase 3: Neo4j Schema Extension (Priority: High)
Extend graph schema with:
```cypher
(:FileResource {path, type, exists})
(:EnvVar {name, required})
(:ConfigKey {section, key, type})

// New relationships:
(Method)-[:READS_FILE]->(FileResource)
(Method)-[:WRITES_FILE]->(FileResource)  
(Method)-[:REQUIRES_ENV]->(EnvVar)
(Method)-[:ACCESSES_CONFIG]->(ConfigKey)
```

#### Phase 4: Integration with Hybrid System (Priority: High)
Modify `analyze_dependencies_and_merge_to_graph()` to:
1. Run Isaac's enhanced analyzer (now with file dependencies)
2. Merge Python dependencies + file dependencies into Neo4j
3. Return complete context including all dependency types

### Success Criteria for MVP

The system is **production-ready** when:

1. ✅ **Complete Context Coverage**: AI agents get structural + relational + file dependencies
2. ✅ **Zero Blind Spots**: No more "I don't know what config this function needs"
3. ✅ **Runtime Accuracy**: Dependencies match actual file access at runtime
4. ✅ **Scale Performance**: File detection adds <20% overhead to analysis time

### Risk Assessment

**Without this fix:**
- ❌ AI agents will confidently make incomplete changes
- ❌ Production systems will fail due to missing file context  
- ❌ Developer trust will be broken by "working" code that crashes
- ❌ The anti-hallucination promise is fundamentally compromised

**Timeline Impact:**
- **Estimated work**: 3-5 days for file dependency detection
- **Total delay to MVP**: 1 week maximum
- **Alternative**: Ship incomplete system that fails in production

### Decision Required

**We cannot ship the MVP without file dependency detection.** This is not an optimization - it's a fundamental requirement for the anti-hallucination system to work as promised.

**Recommendation**: Implement file dependency detection as **Phase 1** before any additional feature work.