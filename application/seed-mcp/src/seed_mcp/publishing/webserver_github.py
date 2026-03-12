#!/usr/bin/env python3
"""
SEED v0 Publishing Platform - GitHub-Based Webserver
Stateless webserver that uses GitHub as transport layer for Carton operations.
"""

import os
import sys
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, '/home/GOD/seed_v0_publishing')

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Import our corrected single authorized.json quarantine system
from seed_quarantine_github_v2 import GitHubQuarantineManager
from redaction_manager import RedactionManager
from auto_redaction_workflow import AutoRedactionWorkflow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SEED GitHub Quarantine Manager",
    description="GitHub-based web interface for reviewing and approving quarantined concepts",
    version="0.2.0"
)

# Initialize GitHub-based quarantine manager
manager = GitHubQuarantineManager(
    github_pat=os.environ.get('GITHUB_PAT'),
    carton_repo_url=os.environ.get('CARTON_REPO_URL')
)

# Initialize redaction manager
redaction_manager = RedactionManager("redacted.json")

# Pydantic models for request/response
class ApprovalRequest(BaseModel):
    reviewer: str = "isaac"
    reason: Optional[str] = None

class RejectionRequest(BaseModel):
    reason: str = "Not suitable for publication"

class ConceptStatusResponse(BaseModel):
    concept_name: str
    status: Optional[str]
    in_quarantine: bool

class RedactionRuleRequest(BaseModel):
    sensitive_term: str
    replacement: str = "[REDACTED]"

class RedactionRuleResponse(BaseModel):
    rules: Dict[str, str]

# API Routes

@app.get("/")
async def root():
    """Serve the main HTML interface."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SEED GitHub Quarantine Manager</title>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: #059669;
                color: white;
                padding: 20px;
                text-align: center;
            }
            .github-badge {
                background: rgba(255,255,255,0.2);
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                margin-left: 10px;
            }
            .controls {
                padding: 20px;
                border-bottom: 1px solid #e5e5e5;
                display: flex;
                gap: 10px;
                align-items: center;
            }
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                transition: background-color 0.2s;
            }
            .btn-primary { background: #059669; color: white; }
            .btn-success { background: #10b981; color: white; }
            .btn-danger { background: #ef4444; color: white; }
            .btn-secondary { background: #6b7280; color: white; }
            .btn:hover { opacity: 0.9; }
            .btn:disabled { opacity: 0.5; cursor: not-allowed; }
            .content {
                display: flex;
                min-height: 600px;
            }
            .quarantine-list {
                width: 400px;
                border-right: 1px solid #e5e5e5;
                overflow-y: auto;
            }
            .concept-item {
                padding: 15px;
                border-bottom: 1px solid #e5e5e5;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            .concept-item:hover { background-color: #f9fafb; }
            .concept-item.selected { background-color: #ecfdf5; border-left: 3px solid #059669; }
            .concept-name { font-weight: 600; margin-bottom: 5px; }
            .concept-meta { font-size: 12px; color: #6b7280; }
            .concept-preview {
                flex: 1;
                padding: 20px;
                overflow-y: auto;
            }
            .concept-actions {
                padding: 20px;
                border-top: 1px solid #e5e5e5;
                display: flex;
                gap: 10px;
                align-items: center;
            }
            .markdown-content {
                line-height: 1.6;
                max-width: none;
            }
            .concept-header {
                border-bottom: 2px solid #059669;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }
            .concept-header h2 {
                margin: 0;
                color: #059669;
            }
            .concept-header p {
                margin: 5px 0 0 0;
                font-style: italic;
                color: #6b7280;
            }
            .markdown-content h1, .markdown-content h2, .markdown-content h3 {
                color: #1f2937;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
            }
            .markdown-content code {
                background: #f1f5f9;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: 'Monaco', 'Consolas', monospace;
            }
            .markdown-content pre {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 16px;
                overflow-x: auto;
            }
            .loading { text-align: center; padding: 40px; color: #6b7280; }
            .error { color: #ef4444; padding: 20px; text-align: center; }
            .success { color: #10b981; padding: 10px; text-align: center; }
            .empty-state { 
                text-align: center; 
                padding: 40px; 
                color: #6b7280;
                font-style: italic;
            }
            .status-indicator {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-github { background: #059669; }
            .info-box {
                background: #ecfdf5;
                border: 1px solid #059669;
                border-radius: 4px;
                padding: 12px;
                margin-bottom: 16px;
                font-size: 14px;
            }
            .redaction-panel {
                border-top: 1px solid #e5e5e5;
                background: #f9fafb;
                padding: 20px;
            }
            .redaction-header h3 {
                margin: 0 0 8px 0;
                color: #374151;
            }
            .redaction-header p {
                margin: 0 0 16px 0;
                color: #6b7280;
                font-size: 14px;
            }
            .add-rule-form {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
            }
            .add-rule-form input {
                padding: 8px 12px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                font-size: 14px;
            }
            .add-rule-form input:first-child {
                flex: 2;
            }
            .add-rule-form input:nth-child(2) {
                flex: 1;
            }
            .rule-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                background: white;
                border: 1px solid #e5e5e5;
                border-radius: 4px;
                margin-bottom: 8px;
            }
            .rule-term {
                font-family: 'Monaco', 'Consolas', monospace;
                background: #f1f5f9;
                padding: 2px 6px;
                border-radius: 3px;
                font-weight: 600;
            }
            .rule-replacement {
                font-family: 'Monaco', 'Consolas', monospace;
                color: #ef4444;
                font-weight: 600;
            }
            .btn-remove {
                background: #ef4444;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                cursor: pointer;
                font-size: 12px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔍 SEED GitHub Quarantine Manager</h1>
                <p>Review and approve concepts for public publishing via GitHub
                   <span class="github-badge">⚡ GitHub-based</span>
                </p>
            </div>
            
            <div class="info-box">
                <span class="status-indicator status-github"></span>
                <strong>GitHub Integration:</strong> This webserver clones your Carton repo from GitHub, 
                performs CRUD operations on authorized.json, and pushes changes back. 
                No local filesystem coupling required!
            </div>
            
            <div class="controls">
                <button class="btn btn-primary" onclick="refreshQuarantine()">🔄 Pull Fresh Data</button>
                <button class="btn btn-secondary" onclick="syncWithGitHub()">🔀 Push to GitHub</button>
                <button class="btn btn-secondary" onclick="toggleRedactionPanel()">🔒 Manage Redactions</button>
                <button class="btn btn-success" onclick="publishToPublic()">🚀 Publish to Public</button>
                <span id="status" class="status-text"></span>
            </div>
            
            <!-- Redaction Management Panel (hidden by default) -->
            <div id="redaction-panel" class="redaction-panel" style="display: none;">
                <div class="redaction-header">
                    <h3>🔒 Redaction Rules Management</h3>
                    <p>Manage exact string matching rules for content redaction</p>
                </div>
                
                <div class="redaction-content">
                    <div class="redaction-controls">
                        <div class="add-rule-form">
                            <input type="text" id="new-term" placeholder="Term to redact..." />
                            <input type="text" id="new-replacement" placeholder="Replacement (default: [REDACTED])" />
                            <button class="btn btn-success" onclick="addRedactionRule()">+ Add Rule</button>
                        </div>
                    </div>
                    
                    <div class="rules-list" id="rules-list">
                        <div class="loading">Loading redaction rules...</div>
                    </div>
                </div>
            </div>
            
            <div class="content">
                <div class="quarantine-list" id="quarantine-list">
                    <div class="loading">Loading quarantine entries...</div>
                </div>
                
                <div class="concept-preview">
                    <div id="concept-content" class="empty-state">
                        Select a concept from the list to preview its content from GitHub
                    </div>
                    
                    <div class="concept-actions" id="concept-actions" style="display: none;">
                        <button class="btn btn-success" onclick="approveConcept()" id="approve-btn">
                            ✅ Approve for Publishing
                        </button>
                        <button class="btn btn-danger" onclick="rejectConcept()" id="reject-btn">
                            ❌ Reject
                        </button>
                        <button class="btn btn-secondary" onclick="needsRevisionConcept()" id="needs-revision-btn">
                            📝 Needs Revision
                        </button>
                        <button class="btn btn-secondary" onclick="needsRedactConcept()" id="needs-redact-btn">
                            🔒 Needs Redaction
                        </button>
                        <span id="action-status"></span>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let currentConcept = null;
            let quarantineEntries = [];

            // Load quarantine entries on page load
            document.addEventListener('DOMContentLoaded', function() {
                refreshQuarantine();
            });

            async function refreshQuarantine() {
                try {
                    showStatus('Pulling fresh data from GitHub...', 'info');
                    const response = await fetch('/api/quarantine');
                    const entries = await response.json();
                    
                    quarantineEntries = entries;
                    renderQuarantineList(entries);
                    showStatus(`Pulled fresh data: ${entries.length} quarantine entries`, 'success');
                } catch (error) {
                    showError('Failed to pull fresh data: ' + error.message);
                }
            }

            function renderQuarantineList(entries) {
                const listEl = document.getElementById('quarantine-list');
                
                if (entries.length === 0) {
                    listEl.innerHTML = '<div class="empty-state">No concepts in quarantine</div>';
                    return;
                }

                const html = entries.map(entry => `
                    <div class="concept-item" onclick="selectConcept('${entry.concept_name}')">
                        <div class="concept-name">${entry.concept_name}</div>
                        <div class="concept-meta">
                            QA: ${entry.qa_id || 'N/A'} | 
                            Type: ${entry.concept_type || 'qa_file'} |
                            Created: ${entry.created_at ? new Date(entry.created_at).toLocaleDateString() : 'Unknown'}
                        </div>
                    </div>
                `).join('');
                
                listEl.innerHTML = html;
            }

            async function selectConcept(conceptName) {
                // Update UI selection
                document.querySelectorAll('.concept-item').forEach(item => {
                    item.classList.remove('selected');
                });
                event.target.closest('.concept-item').classList.add('selected');
                
                currentConcept = conceptName;
                
                try {
                    showStatus('Loading concept content from GitHub...', 'info');
                    
                    // Load concept content from GitHub repo
                    const response = await fetch(`/api/concept/${encodeURIComponent(conceptName)}/content`);
                    const result = await response.json();
                    
                    const contentEl = document.getElementById('concept-content');
                    const actionsEl = document.getElementById('concept-actions');
                    
                    if (result.content) {
                        renderConceptContent(conceptName, result.content, contentEl);
                    } else {
                        contentEl.innerHTML = `
                            <div class="markdown-content">
                                <h2>${conceptName}</h2>
                                <p><em>Content not available (${result.error || 'Unknown error'})</em></p>
                                <p><strong>Note:</strong> Concept will be cloned from GitHub when approved.</p>
                            </div>
                        `;
                    }
                    
                    actionsEl.style.display = 'flex';
                    showStatus('Concept loaded from GitHub', 'success');
                    
                } catch (error) {
                    showError('Failed to load concept content from GitHub: ' + error.message);
                }
            }

            async function approveConcept() {
                if (!currentConcept) return;
                
                if (!confirm(`Approve "${currentConcept}" for public publishing?\n\nThis will:\n1. Clone Carton repo from GitHub\n2. Update authorized.json\n3. Commit and push to GitHub`)) return;
                
                try {
                    showActionStatus('Approving via GitHub...', 'info');
                    
                    const response = await fetch(`/api/approve/${encodeURIComponent(currentConcept)}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ reviewer: 'isaac' })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showActionStatus('✅ Approved and pushed to GitHub!', 'success');
                        // Remove from quarantine list
                        setTimeout(() => {
                            resetConceptView();
                        }, 2000);
                    } else {
                        showActionStatus('❌ Approval failed: ' + (result.error || 'Unknown error'), 'error');
                    }
                    
                } catch (error) {
                    showActionStatus('❌ Approval failed: ' + error.message, 'error');
                }
            }

            async function rejectConcept() {
                if (!currentConcept) return;
                
                const reason = prompt(`Reject "${currentConcept}" - Reason:`, 'Not suitable for publication');
                if (!reason) return;
                
                try {
                    showActionStatus('Rejecting via GitHub...', 'info');
                    
                    const response = await fetch(`/api/reject/${encodeURIComponent(currentConcept)}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ reason: reason })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showActionStatus('✅ Rejected and pushed to GitHub!', 'success');
                        // Remove from quarantine list  
                        setTimeout(() => {
                            resetConceptView();
                        }, 2000);
                    } else {
                        showActionStatus('❌ Rejection failed: ' + (result.error || 'Unknown error'), 'error');
                    }
                    
                } catch (error) {
                    showActionStatus('❌ Rejection failed: ' + error.message, 'error');
                }
            }

            async function needsRevisionConcept() {
                if (!currentConcept) return;
                
                const reason = prompt(`Mark "${currentConcept}" as needs revision - Reason:`, 'Requires content revision before publication');
                if (!reason) return;
                
                try {
                    showActionStatus('Marking as needs revision via GitHub...', 'info');
                    
                    const response = await fetch(`/api/needs_revision/${encodeURIComponent(currentConcept)}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ reason: reason })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showActionStatus('✅ Marked as needs revision!', 'success');
                        setTimeout(() => {
                            resetConceptView();
                        }, 2000);
                    } else {
                        showActionStatus('❌ Failed to mark as needs revision: ' + (result.error || 'Unknown error'), 'error');
                    }
                    
                } catch (error) {
                    showActionStatus('❌ Failed to mark as needs revision: ' + error.message, 'error');
                }
            }

            async function needsRedactConcept() {
                if (!currentConcept) return;
                
                const reason = prompt(`Mark "${currentConcept}" as needs redaction - Reason:`, 'Contains sensitive information requiring redaction');
                if (!reason) return;
                
                try {
                    showActionStatus('Marking as needs redaction via GitHub...', 'info');
                    
                    const response = await fetch(`/api/needs_redact/${encodeURIComponent(currentConcept)}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ reason: reason })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showActionStatus('✅ Marked as needs redaction!', 'success');
                        setTimeout(() => {
                            resetConceptView();
                        }, 2000);
                    } else {
                        showActionStatus('❌ Failed to mark as needs redaction: ' + (result.error || 'Unknown error'), 'error');
                    }
                    
                } catch (error) {
                    showActionStatus('❌ Failed to mark as needs redaction: ' + error.message, 'error');
                }
            }

            async function syncWithGitHub() {
                try {
                    showStatus('Pushing authorized.json to GitHub...', 'info');
                    
                    const response = await fetch('/api/sync', { method: 'POST' });
                    const result = await response.json();
                    
                    if (result.success) {
                        showStatus('✅ Pushed to GitHub successfully', 'success');
                    } else {
                        showStatus('❌ GitHub push failed: ' + (result.error || 'Unknown error'), 'error');
                    }
                    
                } catch (error) {
                    showStatus('❌ GitHub push failed: ' + error.message, 'error');
                }
            }

            async function publishToPublic() {
                if (!confirm('Publish all authorized concepts to public branch?\\n\\nThis will:\\n1. Detect changed content since last publication\\n2. Run auto-redaction on changed files\\n3. Apply all redaction rules\\n4. Publish to #public branch\\n\\nThis may take several minutes.')) {
                    return;
                }

                try {
                    showStatus('🚀 Starting auto-redaction and publishing workflow...', 'info');
                    
                    const response = await fetch('/api/publish_to_public', { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showStatus(`✅ Published successfully! ${result.files_processed} files processed, ${result.rules_added} redaction rules added`, 'success');
                    } else {
                        showStatus('❌ Publishing failed: ' + (result.error || 'Unknown error'), 'error');
                    }
                    
                } catch (error) {
                    showStatus('❌ Publishing failed: ' + error.message, 'error');
                }
            }

            function resetConceptView() {
                refreshQuarantine();
                currentConcept = null;
                document.getElementById('concept-content').innerHTML = '<div class="empty-state">Select a concept from the list to preview its content from GitHub</div>';
                document.getElementById('concept-actions').style.display = 'none';
            }

            function clearStatusAfterDelay(statusEl, delay = 3000) {
                setTimeout(() => {
                    statusEl.textContent = '';
                    statusEl.className = 'status-text';
                }, delay);
            }

            function showStatus(message, type = 'info') {
                const statusEl = document.getElementById('status');
                statusEl.textContent = message;
                statusEl.className = `status-text ${type}`;
                
                if (type === 'success' || type === 'error') {
                    clearStatusAfterDelay(statusEl);
                }
            }

            function showActionStatus(message, type = 'info') {
                const statusEl = document.getElementById('action-status');
                statusEl.textContent = message;
                statusEl.className = `status-text ${type}`;
                
                if (type === 'success' || type === 'error') {
                    clearStatusAfterDelay(statusEl);
                }
            }

            function showError(message) {
                const listEl = document.getElementById('quarantine-list');
                listEl.innerHTML = `<div class="error">${message}</div>`;
            }

            function scrollToTopOfConceptPreview() {
                // Try multiple scroll targets and methods
                const conceptPreview = document.querySelector('.concept-preview');
                const conceptContent = document.getElementById('concept-content');
                
                console.log('Attempting to scroll to top...');
                console.log('conceptPreview element:', conceptPreview);
                console.log('conceptContent element:', conceptContent);
                
                // Try scrolling the concept preview container
                if (conceptPreview) {
                    console.log('Before scroll - conceptPreview.scrollTop:', conceptPreview.scrollTop);
                    conceptPreview.scrollTop = 0;
                    conceptPreview.scrollTo(0, 0);
                    console.log('After scroll - conceptPreview.scrollTop:', conceptPreview.scrollTop);
                }
                
                // Also try scrolling the content element
                if (conceptContent) {
                    conceptContent.scrollTop = 0;
                    conceptContent.scrollTo(0, 0);
                }
                
                // Force scroll the main window as backup
                window.scrollTo(0, 0);
                
                console.log('Scroll attempt completed');
            }
            
            function renderConceptContent(conceptName, markdownContent, contentEl) {
                // Proper markdown rendering using marked.js
                const htmlContent = marked.parse(markdownContent);
                
                contentEl.innerHTML = `
                    <div class="markdown-content">
                        <div class="concept-header">
                            <h2>${conceptName}</h2>
                            <p><em>Content loaded from GitHub repo</em></p>
                        </div>
                        ${htmlContent}
                    </div>
                `;
                
                // Scroll to top of the concept preview area
                scrollToTopOfConceptPreview();
                
                // Intercept concept links to keep them in the interface
                interceptConceptLinks(contentEl);
            }
            
            function interceptConceptLinks(contentEl) {
                // Find all links that look like concept links
                const links = contentEl.querySelectorAll('a[href*=".md"]');
                
                links.forEach(link => {
                    const href = link.getAttribute('href');
                    
                    // Check if it's a concept link pattern: /ConceptName/ConceptName_itself.md
                    const conceptMatch = href.match(/\/([^\/]+)\/[^\/]+\.md$/);
                    if (conceptMatch) {
                        const conceptName = conceptMatch[1];
                        
                        // Prevent default link behavior and load in our interface instead
                        link.addEventListener('click', (e) => {
                            e.preventDefault();
                            
                            // Update the quarantine list selection (if concept exists there)
                            const conceptItems = document.querySelectorAll('.concept-item');
                            conceptItems.forEach(item => {
                                item.classList.remove('selected');
                                if (item.textContent.includes(conceptName)) {
                                    item.classList.add('selected');
                                }
                            });
                            
                            // Load the concept content
                            selectConceptByName(conceptName);
                        });
                        
                        // Add visual indicator that this is an internal link
                        link.style.color = '#059669';
                        link.style.fontWeight = '500';
                        link.title = `Click to view ${conceptName} in this interface`;
                    }
                });
            }
            
            async function selectConceptByName(conceptName) {
                currentConcept = conceptName;
                
                try {
                    showStatus('Loading linked concept...', 'info');
                    
                    // Load concept content
                    const response = await fetch(`/api/concept/${encodeURIComponent(conceptName)}/content`);
                    const result = await response.json();
                    
                    const contentEl = document.getElementById('concept-content');
                    const actionsEl = document.getElementById('concept-actions');
                    
                    if (result.content) {
                        renderConceptContent(conceptName, result.content, contentEl);
                    } else {
                        contentEl.innerHTML = `
                            <div class="markdown-content">
                                <h2>${conceptName}</h2>
                                <p><em>Content not available (${result.error || 'Unknown error'})</em></p>
                                <p><strong>Note:</strong> Concept will be cloned from GitHub when approved.</p>
                            </div>
                        `;
                        // Ensure scroll to top even when content is not available
                        scrollToTopOfConceptPreview();
                    }
                    
                    actionsEl.style.display = 'flex';
                    showStatus('Linked concept loaded', 'success');
                    
                } catch (error) {
                    showError('Failed to load linked concept: ' + error.message);
                }
            }
            
            // Redaction Management Functions
            function toggleRedactionPanel() {
                const panel = document.getElementById('redaction-panel');
                if (panel.style.display === 'none') {
                    panel.style.display = 'block';
                    loadRedactionRules();
                } else {
                    panel.style.display = 'none';
                }
            }
            
            async function loadRedactionRules() {
                try {
                    const response = await fetch('/api/redaction/rules');
                    const data = await response.json();
                    
                    const rulesListEl = document.getElementById('rules-list');
                    if (Object.keys(data.rules).length === 0) {
                        rulesListEl.innerHTML = '<div class="empty-state">No redaction rules configured</div>';
                        return;
                    }
                    
                    rulesListEl.innerHTML = Object.entries(data.rules)
                        .map(([term, replacement]) => `
                            <div class="rule-item">
                                <div>
                                    <span class="rule-term">${term}</span>
                                    <span style="margin: 0 8px;">→</span>
                                    <span class="rule-replacement">${replacement}</span>
                                </div>
                                <button class="btn-remove" onclick="removeRedactionRule('${term}')">✕</button>
                            </div>
                        `).join('');
                } catch (error) {
                    document.getElementById('rules-list').innerHTML = 
                        '<div class="error">Failed to load redaction rules</div>';
                }
            }
            
            async function addRedactionRule() {
                const termInput = document.getElementById('new-term');
                const replacementInput = document.getElementById('new-replacement');
                
                const term = termInput.value.trim();
                if (!term) {
                    showError('Please enter a term to redact');
                    return;
                }
                
                const replacement = replacementInput.value.trim() || '[REDACTED]';
                
                try {
                    const response = await fetch('/api/redaction/rules', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            sensitive_term: term,
                            replacement: replacement
                        })
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        termInput.value = '';
                        replacementInput.value = '';
                        loadRedactionRules();
                        showStatus('Redaction rule added successfully', 'success');
                    } else {
                        showError(result.error || 'Failed to add redaction rule');
                    }
                } catch (error) {
                    showError('Error adding redaction rule: ' + error.message);
                }
            }
            
            async function removeRedactionRule(term) {
                if (!confirm(`Remove redaction rule for "${term}"?`)) {
                    return;
                }
                
                try {
                    const response = await fetch(`/api/redaction/rules/${encodeURIComponent(term)}`, {
                        method: 'DELETE'
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        loadRedactionRules();
                        showStatus('Redaction rule removed successfully', 'success');
                    } else {
                        showError(result.error || 'Failed to remove redaction rule');
                    }
                } catch (error) {
                    showError('Error removing redaction rule: ' + error.message);
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/quarantine")
async def get_quarantine_entries() -> List[Dict[str, Any]]:
    """Get all concepts currently in quarantine."""
    try:
        entries = manager.publishing_review_quarantine()
        logger.info(f"Retrieved {len(entries)} quarantine entries")
        return entries
    except Exception as e:
        logger.error(f"Failed to get quarantine entries: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/concept/{concept_name}/content")
async def get_concept_content(concept_name: str) -> Dict[str, Any]:
    """Get the markdown content of a concept from GitHub repo."""
    try:
        result = manager.get_concept_content(concept_name)
        logger.info(f"Retrieved concept content for {concept_name}")
        return result
    except Exception as e:
        logger.error(f"Failed to get concept content for {concept_name}: {e}")
        logger.debug(traceback.format_exc())
        return {"error": str(e)}

@app.post("/api/approve/{concept_name}")
async def approve_concept(concept_name: str, request: ApprovalRequest) -> Dict[str, Any]:
    """Approve a concept for public publishing via GitHub."""
    try:
        success = manager.publishing_authorize_for_publishing(concept_name, request.reviewer)
        if success:
            logger.info(f"Approved concept via GitHub: {concept_name} by {request.reviewer}")
            return {"success": True, "message": f"Approved {concept_name} for publication via GitHub"}
        else:
            logger.error(f"Failed to approve concept via GitHub: {concept_name}")
            return {"success": False, "error": "GitHub approval operation failed"}
    except Exception as e:
        logger.error(f"Error approving concept {concept_name} via GitHub: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reject/{concept_name}")
async def reject_concept(concept_name: str, request: RejectionRequest) -> Dict[str, Any]:
    """Reject a concept from being published via GitHub."""
    try:
        success = manager.publishing_reject_concept(concept_name, request.reason)
        if success:
            logger.info(f"Rejected concept via GitHub: {concept_name} - {request.reason}")
            return {"success": True, "message": f"Rejected {concept_name} via GitHub"}
        else:
            logger.error(f"Failed to reject concept via GitHub: {concept_name}")
            return {"success": False, "error": "GitHub rejection operation failed"}
    except Exception as e:
        logger.error(f"Error rejecting concept {concept_name} via GitHub: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/needs_revision/{concept_name}")
async def needs_revision_concept(concept_name: str, request: RejectionRequest) -> Dict[str, Any]:
    """Mark a concept as needs revision via GitHub."""
    try:
        success = manager.publishing_needs_revision_concept(concept_name, request.reason)
        if success:
            logger.info(f"Marked concept as needs revision via GitHub: {concept_name} - {request.reason}")
            return {"success": True, "message": f"Marked {concept_name} as needs revision via GitHub"}
        else:
            logger.error(f"Failed to mark concept as needs revision via GitHub: {concept_name}")
            return {"success": False, "error": "GitHub needs revision operation failed"}
    except Exception as e:
        logger.error(f"Error marking concept {concept_name} as needs revision via GitHub: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/needs_redact/{concept_name}")
async def needs_redact_concept(concept_name: str, request: RejectionRequest) -> Dict[str, Any]:
    """Mark a concept as needs redaction via GitHub."""
    try:
        success = manager.publishing_needs_redact_concept(concept_name, request.reason)
        if success:
            logger.info(f"Marked concept as needs redaction via GitHub: {concept_name} - {request.reason}")
            return {"success": True, "message": f"Marked {concept_name} as needs redaction via GitHub"}
        else:
            logger.error(f"Failed to mark concept as needs redaction via GitHub: {concept_name}")
            return {"success": False, "error": "GitHub needs redaction operation failed"}
    except Exception as e:
        logger.error(f"Error marking concept {concept_name} as needs redaction via GitHub: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync")
async def sync_authorization() -> Dict[str, Any]:
    """Push current authorized.json back to GitHub repository."""
    try:
        success = manager.sync_authorization_file()
        if success:
            logger.info("GitHub push successful")
            return {"success": True, "message": "authorized.json pushed to GitHub successfully"}
        else:
            logger.error("GitHub push failed")
            return {"success": False, "error": "GitHub push operation failed"}
    except Exception as e:
        logger.error(f"Error during GitHub push: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status/{concept_name}")
async def get_concept_status(concept_name: str) -> ConceptStatusResponse:
    """Check the authorization status of a concept."""
    try:
        status = manager.get_authorization_status(concept_name)
        in_quarantine = status == "quarantine"
        
        return ConceptStatusResponse(
            concept_name=concept_name,
            status=status,
            in_quarantine=in_quarantine
        )
    except Exception as e:
        logger.error(f"Error checking status for concept {concept_name}: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/authorized")
async def get_authorized_concepts() -> List[str]:
    """Get list of all approved concepts."""
    try:
        approved = manager.get_approved_concepts()
        logger.info(f"Retrieved {len(approved)} approved concepts")
        return approved
    except Exception as e:
        logger.error(f"Failed to get approved concepts: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Redaction Management API Endpoints

@app.get("/api/redaction/rules")
async def get_redaction_rules() -> RedactionRuleResponse:
    """Get all redaction rules."""
    try:
        rules = redaction_manager.get_rules()
        logger.info(f"Retrieved {len(rules)} redaction rules")
        return RedactionRuleResponse(rules=rules)
    except Exception as e:
        logger.error(f"Failed to get redaction rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/redaction/rules")
async def add_redaction_rule(request: RedactionRuleRequest) -> Dict[str, Any]:
    """Add a new redaction rule."""
    try:
        success = redaction_manager.add_rule(request.sensitive_term, request.replacement)
        if success:
            logger.info(f"Added redaction rule: '{request.sensitive_term}' → '{request.replacement}'")
            return {"success": True, "message": f"Added redaction rule for '{request.sensitive_term}'"}
        else:
            logger.error(f"Failed to add redaction rule: {request.sensitive_term}")
            return {"success": False, "error": "Failed to save redaction rule"}
    except Exception as e:
        logger.error(f"Error adding redaction rule '{request.sensitive_term}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/redaction/rules/{sensitive_term}")
async def remove_redaction_rule(sensitive_term: str) -> Dict[str, Any]:
    """Remove a redaction rule."""
    try:
        success = redaction_manager.remove_rule(sensitive_term)
        if success:
            logger.info(f"Removed redaction rule: '{sensitive_term}'")
            return {"success": True, "message": f"Removed redaction rule for '{sensitive_term}'"}
        else:
            logger.warning(f"Redaction rule not found: '{sensitive_term}'")
            return {"success": False, "error": f"Redaction rule for '{sensitive_term}' not found"}
    except Exception as e:
        logger.error(f"Error removing redaction rule '{sensitive_term}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/redaction/preview")
async def preview_redactions(request: Dict[str, str]) -> Dict[str, Any]:
    """Preview redactions that would be applied to content."""
    try:
        content = request.get("content", "")
        context_chars = request.get("context_chars", 30)
        
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        previews = redaction_manager.preview_redactions(content, int(context_chars))
        logger.info(f"Generated {len(previews)} redaction previews")
        
        return {
            "success": True,
            "previews": previews,
            "total_redactions": len(previews)
        }
    except Exception as e:
        logger.error(f"Error generating redaction preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Publishing workflow endpoint

@app.post("/api/publish_to_public")
async def publish_to_public() -> Dict[str, Any]:
    """Execute the complete auto-redaction and publishing workflow."""
    try:
        logger.info("Starting auto-redaction and publishing workflow")
        
        # Create auto-redaction workflow instance with proper credentials
        # Use the concepts directory from the already-cloned repo
        repo_concepts_dir = str(manager.temp_repo_dir / "concepts")
        workflow = AutoRedactionWorkflow(
            repo_concepts_dir,
            github_pat=manager.github_pat,
            carton_repo_url=manager.carton_repo_url
        )
        
        # Execute the workflow
        result = await workflow.execute_auto_redaction_workflow()
        
        logger.info(f"Auto-redaction workflow completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Auto-redaction workflow failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Workflow failed: {str(e)}",
            "files_processed": 0,
            "rules_added": 0
        }

# Health check endpoint

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "mode": "github"}

if __name__ == "__main__":
    import uvicorn
    
    # Configuration
    host = os.environ.get("WEBSERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("WEBSERVER_PORT", "8081"))
    
    logger.info(f"Starting SEED GitHub Quarantine Manager webserver on {host}:{port}")
    logger.info(f"GitHub repo: {manager.carton_repo_url}")
    logger.info(f"Temp repo directory: {manager.temp_repo_dir}")
    logger.info("Using single authorized.json architecture")
    
    uvicorn.run(app, host=host, port=port)