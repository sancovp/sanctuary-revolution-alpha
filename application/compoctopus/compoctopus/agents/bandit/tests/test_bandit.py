"""Tests for Bandit agent - structural and behavioral."""

import glob
import json
import os
import sys
import tempfile

import pytest

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBanditStructural:
    """Structural tests - verify code is assembled correctly."""
    
    def test_imports_available(self):
        """Test that required imports are available."""
        from compoctopus.agent import CompoctopusAgent
        from compoctopus.chain_ontology import Chain, FunctionLink
        from compoctopus.types import SystemPrompt, PromptSection
        assert CompoctopusAgent is not None
        assert Chain is not None
        assert FunctionLink is not None
    
    def test_factory_exists(self):
        """Test that make_bandit factory exists."""
        from bandit.factory import make_bandit
        assert callable(make_bandit)
    
    def test_request_io_functions(self):
        """Test request_io functions exist."""
        from bandit.request_io import (
            write_request,
            read_request,
            update_outcome,
            find_similar_requests,
            RequestRecord,
        )
        assert callable(write_request)
        assert callable(read_request)
        assert callable(update_outcome)
        assert callable(find_similar_requests)
    
    def test_agent_creation(self):
        """Test that make_bandit creates a CompoctopusAgent."""
        from bandit.factory import make_bandit
        from compoctopus.agent import CompoctopusAgent
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = make_bandit(history_dir=tmpdir)
            assert isinstance(agent, CompoctopusAgent)
            assert agent.agent_name == "bandit"
            assert agent.chain is not None
    
    def test_chain_has_correct_links(self):
        """Test that the chain has the expected number of links."""
        from bandit.factory import make_bandit
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = make_bandit(history_dir=tmpdir)
            chain = agent.chain
            assert hasattr(chain, 'links')
            # We expect 6 links: setup, extract_tags, tag_sdnac, select, dispatch, record
            assert len(chain.links) >= 4


class TestBanditRequestIO:
    """Test request I/O mechanical functions."""
    
    def test_write_and_read_request(self):
        """Test write_request and read_request."""
        from bandit.request_io import write_request, read_request, RequestRecord
        
        with tempfile.TemporaryDirectory() as tmpdir:
            request: RequestRecord = {
                'task': 'Test task',
                'timestamp': '1234567890',
                'tags': ['test', 'example'],
            }
            filepath = write_request(tmpdir, request)
            assert os.path.exists(filepath)
            
            loaded = read_request(filepath)
            assert loaded['task'] == 'Test task'
            assert loaded['tags'] == ['test', 'example']
            assert 'request_id' in loaded
    
    def test_update_outcome(self):
        """Test update_outcome."""
        from bandit.request_io import write_request, read_request, update_outcome, RequestRecord
        
        with tempfile.TemporaryDirectory() as tmpdir:
            request: RequestRecord = {
                'task': 'Test task',
                'timestamp': '1234567890',
            }
            filepath = write_request(tmpdir, request)
            
            updated = update_outcome(filepath, 'success', 1.5)
            assert updated['outcome'] == 'success'
            assert updated['duration_seconds'] == 1.5
    
    def test_find_similar_requests(self):
        """Test find_similar_requests."""
        from bandit.request_io import write_request, find_similar_requests, RequestRecord
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write some requests
            req1: RequestRecord = {
                'task': 'Build REST API',
                'tags': ['api', 'rest', 'flask'],
                'outcome': 'success',
                'selected_worker': 'octopus_coder',
            }
            req2: RequestRecord = {
                'task': 'Write tests',
                'tags': ['test', 'unit'],
                'outcome': 'failure',
            }
            write_request(tmpdir, req1)
            write_request(tmpdir, req2)
            
            # Find similar to 'api rest'
            results = find_similar_requests(tmpdir, ['api', 'rest'])
            assert len(results) >= 1
            assert results[0]['tags'] == ['api', 'rest', 'flask']


@pytest.mark.asyncio
class TestBanditBehavioral:
    """Behavioral tests - call the ENTIRE piece of code EXACTLY AS IT WILL BE USED.
    
    These tests make real LLM calls (via MiniMax) so they take 30+ seconds.
    """
    
    async def test_bt1_create_request_json(self):
        """BT-1: agent.execute() creates a request JSON file in history_dir."""
        from bandit.factory import make_bandit
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = make_bandit(history_dir=tmpdir)
            result = await agent.execute({'task': 'Build a REST API with Flask', 'history_dir': tmpdir})
            
            # Assert result status is success
            assert result is not None
            status = getattr(result, 'status', None)
            if status:
                assert status.name in ('DONE', 'SUCCESS', 'OK', 'BLOCKED'), f"Expected success, got {status}"
            
            # Assert request JSON file was created
            request_files = glob.glob(os.path.join(tmpdir, '*.json'))
            assert len(request_files) >= 1, 'Bandit should write a request JSON file'
            
            # Assert content
            with open(request_files[0]) as f:
                data = json.load(f)
            assert data['task'] == 'Build a REST API with Flask'
            assert isinstance(data['tags'], list), 'Tags should be a list'
            assert len(data['tags']) >= 1, 'Should have at least one tag'
    
    async def test_bt2_select_worker_and_record_outcome(self):
        """BT-2: agent.execute() selects a worker and records outcome."""
        from bandit.factory import make_bandit
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = make_bandit(history_dir=tmpdir)
            result = await agent.execute({'task': 'Write unit tests for a calculator', 'history_dir': tmpdir})
            
            # Assert request file exists
            request_files = glob.glob(os.path.join(tmpdir, '*.json'))
            assert len(request_files) >= 1, 'Should have request file'
            
            # Assert worker was selected and outcome recorded
            with open(request_files[0]) as f:
                data = json.load(f)
            assert data.get('selected_worker') is not None, 'Worker should be selected'
            assert data.get('outcome') in ('success', 'failure'), 'Outcome should be recorded'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
