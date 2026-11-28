import io
import unittest
import pymupdf
import test_workflows as workflows
from navigator.media import scanned

class Kiosk(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=workflows.Integration.asyncSetUp
    asyncTearDown=workflows.Integration.asyncTearDown
    post=workflows.Integration.post
    async def test_same_browser_two_customers_and_return(self):
        member=(await self.post('profile',{'name':'Rao','consent':True,'answers':{'age':70,'citizen':'yes','state':'AP'}}))['profile']
        await self.post('confirm scan',{'name':'Rao'},profile=member)
        pdf=await self.a.get('/api/report/'+member)
        with pymupdf.open(stream=pdf.content,filetype='pdf') as doc:
            text=''.join(p.get_text() for p in doc)
        self.assertIn('Welfare report for Rao',text)
        self.assertIn('Possible matches',text)
        archive=(await self.post('workspace',profile=member))['reports'][0]['id']
        await self.a.post('/api/visit/finish',json={})
        self.assertEqual((await self.a.get('/api/me')).json(),dict(profiles=[],admin=False,active=False))
        other=(await self.a.post('/api/visit/new',json={})).json();self.a.headers['X-Visit']=other['ticket']
        self.assertEqual((await self.a.get('/api/me')).json()['profiles'],[])
        self.assertEqual((await self.a.get('/api/report/'+member+'/'+archive)).status_code,404)
        back=(await self.a.post('/api/visit/resume',json={'code':self.visit['code']})).json();self.a.headers['X-Visit']=back['ticket']
        self.assertEqual((await self.post('workspace',profile=member))['scan']['name'],'Rao')
        self.assertEqual((await self.a.get('/api/report/'+member+'/'+archive)).content,pdf.content)

    async def test_public_dashboard_registration_and_independent_member_histories(self):
        self.a.headers.pop('X-Visit')
        self.assertEqual((await self.a.get('/')).status_code,200)
        self.assertFalse((await self.a.get('/api/me')).json()['active'])
        self.assertTrue((await self.a.get('/api/catalog')).json()['schemes'])
        code=(await self.a.post('/api/visit/register',json={})).json()['code']
        self.assertEqual((await self.a.get('/api/me')).json()['profiles'],[])
        self.a.headers['X-Visit']=(await self.a.post('/api/visit/resume',json={'code':code})).json()['ticket']
        members=[(await self.post('profile',{'name':name,'consent':True}))['profile'] for name in ['Rao','Sita']]
        first,second=members
        await self.post('navigator progress',{'answers':{'age':70}},profile=first)
        await self.post('screen',{'origin':'navigator','save':True,'answers':{'age':70,'citizen':'yes'}},'ayushman',first)
        await self.post('screen',{'save':True,'answers':{'age':70,'citizen':'yes'}},'ayushman',first)
        await self.post('simulate',{'save':True,'answers':{'age':69,'citizen':'yes'}},'ayushman',first)
        for name in ['Rao A','Rao B']:await self.post('confirm scan',{'name':name},profile=first)
        for origin in ['docs','draft']:
            await self.post('save draft',{'origin':origin,'fields':{},'ready':[]},'ayushman',first)
        saved=await self.post('workspace',profile=first)
        self.assertEqual(saved['profile']['answers']['age'],70)
        self.assertEqual({e['kind'] for e in saved['activity']},{'AI Navigator','Eligibility checker','What-if simulator','Document scanner','Document checklist','Application assistant'})
        self.assertEqual(len([e for e in saved['activity'] if e['kind']=='Document scanner']),2)
        self.assertEqual((await self.post('workspace',profile=second))['activity'],[])
        pdf=await self.a.get('/api/report/'+first)
        with pymupdf.open(stream=pdf.content,filetype='pdf') as doc:
            text=''.join(p.get_text() for p in doc)
        self.assertIn('Rao A',text)
        self.assertIn('Rao B',text)
        self.assertIn('What-if simulator',text)

    def test_structured_pages_and_inline_labels(self):
        with pymupdf.open() as doc:
            doc.new_page().insert_text((40,60),'Name: Rao Demo    District: Mysuru')
            doc.new_page().insert_text((40,60),'Village: Example')
            result=scanned(doc.tobytes(),'sample.pdf','en')
        self.assertEqual(result['fields'],{'name':'Rao Demo','district':'Mysuru','village':'Example'})
        self.assertEqual(len(result['pages']),2)
        self.assertIn('District: Mysuru',result['pages'][0]['lines'])

    async def test_restore_missing_admin_file_without_changing_household(self):
        from navigator import store
        member = (await self.post('profile', {'name':'Sample', 'consent':True}))['profile']
        path = store.DATA / 'ADMIN_FIRST_LOGIN.txt'
        first = path.read_text().strip()
        path.unlink()
        store.init()
        self.assertFalse(path.exists())
        self.assertEqual((await self.a.post('/api/admin/login', json={'password':first})).status_code, 200)
        store.init(issue_new_admin=True)
        recovered = path.read_text().strip()
        self.assertNotEqual(first, recovered)
        self.assertEqual((await self.a.post('/api/admin/login', json={'password':first})).status_code, 403)
        self.assertEqual((await self.a.post('/api/admin/login', json={'password':recovered})).status_code, 200)
        self.assertEqual((await self.post('workspace', profile=member))['profile']['name'], 'Sample')
