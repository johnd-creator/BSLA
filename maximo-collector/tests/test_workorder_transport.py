import unittest
from types import SimpleNamespace
from unittest.mock import patch
from src.adapters.maximo.oslc_client import OslcClient,OslcError,OslcAuthExpiredError,_validate_wo_url
from src.config import MaximoConfig
class Resp:
 def __init__(self,payload=None,code=200):self.status_code=code;self.content=b'{}';self.headers={};self.payload=payload
 def json(self):return self.payload
 def raise_for_status(self):pass
class Auth:
 def __init__(self):self.session=SimpleNamespace(headers={},cookies=[]);self.calls=0
 def ensure_logged_in(self):pass
 def handle_expiry(self):self.calls+=1
class TransportTest(unittest.TestCase):
 def make(self,responses):
  a=Auth();c=OslcClient(MaximoConfig(base_url='https://example.test/maximo',rate_limit_seconds=0),a)
  requests=[];it=iter(responses)
  def get(path):requests.append(path);return next(it)
  c.get=get;return c,a,requests
 def test_auth_expiry_retries_same_page_once(self):
  c,a,r=self.make([Resp(code=401),Resp({'_member':[{'wonum':'BSR1'}]})])
  with patch('src.adapters.maximo.oslc_client.MaximoAuth.looks_expired',side_effect=lambda r:r.status_code==401):
   self.assertEqual(len(list(c.iterate('mxwodetail',max_pages=1))),1)
  self.assertEqual(a.calls,1);self.assertEqual(len(r),2);self.assertEqual(r[0],r[1]);self.assertEqual(c.last_iteration_pages,1)
 def test_nested_or_later_iterator_does_not_repeat_auth_refresh(self):
  c,a,r=self.make([Resp(code=401),Resp({'_member':[]}),Resp(code=401)])
  with patch('src.adapters.maximo.oslc_client.MaximoAuth.looks_expired',side_effect=lambda r:r.status_code==401):
   list(c.iterate('mxwodetail',max_pages=1))
   with self.assertRaises(OslcAuthExpiredError):list(c.iterate('mxwodetail',max_pages=1))
  self.assertEqual(a.calls,1)
 def test_second_expiry_stops(self):
  c,a,r=self.make([Resp(code=401),Resp(code=401)])
  with patch('src.adapters.maximo.oslc_client.MaximoAuth.looks_expired',side_effect=lambda r:r.status_code==401):
   with self.assertRaises(OslcAuthExpiredError):list(c.iterate('mxwodetail',max_pages=1))
  self.assertEqual(a.calls,1);self.assertEqual(len(r),2)
 def test_query_relative_continuation_preserves_collection(self):
  c,a,r=self.make([Resp({'_member':[],'nextPage':'?p=2'}),Resp({'_member':[]})])
  list(c.iterate('mxwodetail',max_pages=2));self.assertEqual(r[1],'/oslc/os/mxwodetail?p=2')
 def test_wrong_object_rdf_resource_never_fetched(self):
  c,a,r=self.make([Resp({'_member':[{'rdf:resource':'https://example.test/maximo/oslc/os/mxperson/1'}]})])
  with self.assertRaises(OslcError):list(c.iterate('mxwodetail',select=['wonum']))
  self.assertEqual(len(r),1)
 def test_encoded_traversal_and_foreign_collection_rejected(self):
  for url in ['/maximo/oslc/os/mxwodetail/../mxperson/1','/maximo/oslc/os/mxwodetail/%2e%2e/mxperson/1','/maximo/oslc/os/mxwodetail/%252e%252e/mxperson/1','/maximo/oslc/os/mxwodetailx/1']:
   with self.assertRaises(OslcError):_validate_wo_url(url,'https://example.test/maximo','/oslc/os/mxwodetail',detail=True)
 def test_root_relative_link_never_duplicates_context_path(self):
  a=Auth();c=OslcClient(MaximoConfig(base_url='https://example.test/maximo',rate_limit_seconds=0),a);calls=[]
  def request(method,url,**kw):calls.append((url,kw));return Resp({})
  c._session.request=request;c.get('/maximo/oslc/os/mxwodetail?p=2')
  self.assertEqual(calls[0][0],'https://example.test/maximo/oslc/os/mxwodetail?p=2');self.assertFalse(calls[0][1]['allow_redirects'])
