"""Offline integration tests. Each test database is private to this process."""
import asyncio
import base64
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import fitz
from PIL import Image,ImageDraw,ImageFont
from navigator import ai,store,ops
from navigator.app import app,init,housekeep
from navigator.media import pdf_report,scanned
from navigator.rules import evaluate,validate_answers,validate_scheme
H={'X-Navigator':'local'}
class Integration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from unit_database import isolated
        isolated(self)
        self.temp=tempfile.TemporaryDirectory();self.location=patch.object(store,'DATA',Path(self.temp.name));self.location.start()
        init()
        self.a=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://127.0.0.1',headers=H)
        await self.a.get('/api/catalog')
        self.visit=(await self.a.post('/api/visit/new',json={})).json()
        self.a.headers['X-Visit']=self.visit['ticket']
    async def asyncTearDown(self):
        await self.a.aclose();self.location.stop();self.temp.cleanup()
    async def post(self,action,data=None,sid='',profile='',admin=False):
        url='/api/admin' if admin else '/api/citizen'
        r=await self.a.post(url,json=dict(action=action,data=data or {},sid=sid,profile=profile))
        self.assertEqual(r.status_code,200,r.text);return r.json()
    async def signin(self):
        password=(store.DATA/'ADMIN_FIRST_LOGIN.txt').read_text().strip()
        r=await self.a.post('/api/admin/login',json={'password':password});self.assertEqual(r.status_code,200)
    async def test_citizen_journey_isolation_reminders_and_export(self):
        p=(await self.post('profile',{'name':'Demo Senior','consent':True}))['profile']
        second=(await self.post('profile',{'name':'Demo Student','consent':True}))['profile']
        a={'age':70,'citizen':'yes'}
        r=await self.post('screen',{'answers':a,'save':True},'ayushman',p)
        self.assertEqual(r['results'][0]['status'],'preliminary eligible')
        sim=await self.post('simulate',{'answers':dict(a,age=69),'save':True},'ayushman',p)
        self.assertEqual(sim['results'][0]['status'],'not eligible')
        self.assertEqual((await self.post('workspace',profile=p))['profile']['answers'],a)
        self.assertEqual((await self.post('workspace',profile=second))['profile']['answers'],{})
        draft=await self.post('save draft',{'fields':{'Applicant name':'Demo Senior'},'ready':[]},'ayushman',p)
        self.assertEqual(draft['status'],'Documents pending')
        await self.post('preferences',{'documents':True,'matches':True},profile=p)
        b=await self.post('workspace',profile=p);self.assertGreaterEqual(len(b['reminders']),2)
        await self.post('reminder',{'id':b['reminders'][0]['id'],'snooze':True},profile=p)
        self.assertEqual(len((await self.post('export',profile=p))['drafts']),1)
        pdf=await self.a.get('/api/report/'+p+'?sid=ayushman')
        self.assertTrue(pdf.content.startswith(b'%PDF'));doc=fitz.open(stream=pdf.content,filetype='pdf');self.assertIn('Demo Senior',''.join(page.get_text() for page in doc))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://localhost',headers=H) as other:
            self.assertEqual((await other.get('/api/report/'+p)).status_code,401)
        await self.post('delete profile',profile=p)
        self.assertEqual((await self.a.get('/api/report/'+p)).status_code,404)
    async def test_admin_lifecycle_and_restore(self):
        denied=await self.a.post('/api/admin',json={'action':'overview'});self.assertEqual(denied.status_code,403)
        await self.signin()
        with patch.object(ai,'model_health',return_value={'online':False,'models':[]}):
            view=await self.post('overview',admin=True)
        self.assertTrue(view['health']['db'].startswith('MySQL'))
        snap=await self.post('backup',admin=True)
        self.assertNotIn('profiles',snap);self.assertNotIn('password',str(snap['settings']))
        s=next(v['scheme'] for v in view['schemes'] if v['sid']=='ujjwala')
        draft=await self.post('scheme',{'scheme':s,'stage':'draft','expected':s['version']},admin=True)
        self.assertGreater(draft['version'],s['version'])
        stale=await self.a.post('/api/admin',json={'action':'scheme','data':{'scheme':s,'stage':'publish','expected':s['version']}})
        self.assertEqual(stale.status_code,422)
        await self.post('scheme',{'scheme':draft,'stage':'publish','expected':draft['version']},admin=True)
        await self.post('restore',{'confirm':'RESTORE','backup':snap},admin=True)
        report=await self.post('benchmark',admin=True);self.assertEqual(report['correct'],report['total']);self.assertGreaterEqual(report['total'],30)
        await self.post('logout',admin=True)
        self.assertEqual((await self.a.post('/api/admin',json={'action':'overview'})).status_code,403)
    async def test_policy_ingestion_real_pdf_and_duplicate(self):
        content=pdf_report('Synthetic policy fixture',[('Rules',['This is synthetic policy evidence for software testing.'])])
        meta=('ayushman','https://nha.gov.in/','Synthetic fixture','Testing only','2026-11-24','')
        res=ops.ingest(*meta,content,'fixture.pdf','en')
        ops.ingest(*meta,content,'fixture.pdf','en')
        with store.db() as c:
            cnt=c.execute('SELECT COUNT(*) FROM sources WHERE body LIKE ?',('%'+res['file_hash']+'%',)).fetchone()[0]
            self.assertEqual(cnt,res['chunks']);self.assertNotIn('Synthetic policy fixture',[x['title'] for x in store.evidence(c)])
        await self.signin()
        with store.db() as c:keys=[r[0] for r in c.execute('SELECT id FROM sources WHERE body LIKE ?',('%'+res['file_hash']+'%',))]
        await self.post('source status',{'ids':keys,'active':True,'reviewed':True},admin=True)
        with store.db() as c:self.assertIn('Synthetic fixture',[x['title'] for x in store.evidence(c)])
        await self.post('source status',{'ids':keys,'active':False},admin=True)
    async def test_corpus_validation_and_three_valued_rules(self):
        with store.db() as c:
            refs={s['id']:s for s in store.evidence(c)};ss={s['id']:s for s in store.policy(c)}
        for s in ss.values():validate_scheme(s,refs,True)
        for f in store.load_file('benchmark'):
            with self.subTest(f=f['case'],sid=f['sid']):self.assertEqual(evaluate(ss[f['sid']],f['answers'],refs)['status'],f['expected'])
        self.assertEqual(evaluate(ss['ayushman'],{'age':0,'citizen':'yes'},refs)['status'],'not eligible')
        self.assertEqual(evaluate(ss['ayushman'],{'age':'unknown','citizen':'yes'},refs)['status'],'more information needed')
        self.assertEqual(evaluate(ss['ayushman'],{'age':75,'citizen':'yes'},{})['status'],'more information needed')
        with self.assertRaises(ValueError):validate_answers({'age':-10})
    async def test_local_ai_transport_and_real_retrieval(self):
        with patch.object(ai,'chat',side_effect=httpx.ConnectError('offline')):
            result=await self.post('ask',{'question':'What Aadhaar documents are needed?','lang':'te'},'ayushman')
        self.assertIn('source excerpts',result['mode']);self.assertIn('A2',[r['id'] for r in result['sources']])
        with patch.object(ai,'chat',return_value='See the official record [BAD].'):
            r=await self.post('ask',{'question':'Aadhaar document'},'ayushman');self.assertIn('citation check',r['mode'])
        r=await self.post('ask',{'question':'xyzzyzzy'},'ayushman');self.assertEqual(r['mode'],'no evidence')
    async def test_ocr_and_upload_rejection(self):
        data=pdf_report('Sample form',[('Applicant',['Name: Sample User','Village: Demo Place'])])
        r=await self.a.post('/api/scan',files={'file':('sample.pdf',data,'application/pdf')},data={'lang':'en'})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['fields']['name'],'Sample User')
        bad=await self.a.post('/api/scan',files={'file':('sample.exe',b'bad','application/octet-stream')},data={'lang':'en'});self.assertEqual(bad.status_code,422)
    async def test_csrf_and_malformed_inputs(self):
        r=await self.a.post('/api/citizen',headers={'Origin':'https://example.org'},json={'action':'profile'});self.assertEqual(r.status_code,403)
        r=await self.a.post('/api/citizen',json={'action':'profile','data':{'name':'Demo','consent':False}});self.assertEqual(r.status_code,422)
        r=await self.a.post('/api/citizen',json={'action':'screen','data':{'answers':{'age':'hello'}}});self.assertEqual(r.status_code,422)
    async def test_config_and_conditional_checklist(self):
        p=(await self.post('profile',{'name':'Demo','consent':True}))['profile']
        s=next(x for x in (await self.a.get('/api/catalog')).json()['schemes'] if x['id']=='ujjwala')
        ready=[x['label'] for x in s['docs'] if not x['when']]
        d={'ready':ready,'fields':{k:'Example' for k in s['fields']},'address':'no'}
        self.assertEqual((await self.post('save draft',d,s['id'],p))['status'],'Ready to apply')
        self.assertEqual((await self.post('save draft',dict(d,address='yes'),s['id'],p))['status'],'Documents pending')
    async def test_installed_tesseract_actual_image(self):
        import shutil
        if not shutil.which('tesseract'):self.skipTest('Tesseract binary unavailable')
        im=Image.new('RGB',(920,180),'white');draw=ImageDraw.Draw(im)
        try:f=ImageFont.truetype('DejaVuSans.ttf',45)
        except OSError:f=ImageFont.load_default(size=45)
        draw.text((20,35),'Name: Demo Citizen',font=f,fill='black');buf=io.BytesIO();im.save(buf,'PNG')
        r=scanned(buf.getvalue(),'sample.png','en');self.assertIn('Demo',r['text']);self.assertGreater(r['confidence'][0],50)
if __name__=='__main__':unittest.main()
