"""Controlled model-adapter tests. Real model generation must be measured on the target laptop."""
import os,tempfile,unittest
from unittest.mock import patch
from navigator import ai,ops,store
class ModelContract(unittest.TestCase):
    def setUp(self):
        from unit_database import isolated
        isolated(self)
        self.dir=tempfile.TemporaryDirectory();self.patch=patch.object(store,'DATA',__import__('pathlib').Path(self.dir.name));self.patch.start();store.init()
    def tearDown(self):self.patch.stop();self.dir.cleanup()
    def test_local_embed_index_retry_and_rag_verifier(self):
        calls=[]
        def endpoint(cfg,path,payload=None,timeout=75):
            calls.append(path)
            if path=='embed':
                batch=payload['input'];return {'embeddings':[[1.0,0.0] for _ in (batch if isinstance(batch,list) else [batch])]}
            if path=='chat':
                if payload['messages'][0]['content'].startswith('Check every'):return {'message':{'content':'SUPPORTED'}}
                return {'message':{'content':'Use the Aadhaar enrolment document [A2].'}}
            return {'models':[{'name':'test:local'}]}
        with patch.object(ai,'api',side_effect=endpoint),patch.object(ai,'collection',side_effect=ImportError()):
            r=ai.build_index();self.assertGreater(r['chunks'],20);n=calls.count('embed');ai.build_index();self.assertEqual(calls.count('embed'),n)
            a=ai.ask('Aadhaar documents enrolment','ayushman');self.assertEqual(a['mode'],'Ollama + RAG');self.assertEqual(a['retriever'],'MySQL vector + keyword')
            r=ops.research('test:local',3,[{'sid':'ayushman','question':'Aadhaar documents','source':'A2'}],'v1')
            self.assertGreater(r['experiment_id'],0)
    def test_verifier_abstention(self):
        with patch.object(ai,'chat',side_effect=['An unsupported statement [A2].','INSUFFICIENT']):
            x=ai.ask('Aadhaar documents enrolment','ayushman');self.assertIn('support check',x['mode']);self.assertNotIn('An unsupported statement',x['answer'])
