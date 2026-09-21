import importlib.util,io,subprocess,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('launcher',str(Path(__file__).with_name('2026-09-08-hermes-lab-trivy-launcher.py')));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Tests(unittest.TestCase):
 def run_case(self,results):
  calls=[];out=io.BytesIO();err=io.BytesIO()
  def runner(command,**kw):
   calls.append((command,kw['timeout'],kw['env']['GODEBUG']))
   code,body,error=results[min(len(calls)-1,len(results)-1)]
   kw['stdout'].write(body)
   return subprocess.CompletedProcess(command,code,stderr=error)
  status=module.scan(['image','--config','/dev/null','pinned-image'],runner=runner,monotonic=lambda:10,pause=lambda _:None,output=out,errors=err)
  for command,timeout,dns in calls:
   self.assertEqual(command,[module.BINARY,'image','--config','/dev/null','pinned-image']);self.assertEqual(timeout,900);self.assertEqual(dns,'netdns=go')
  return status,out.getvalue(),err.getvalue(),len(calls)
 def test_success_once(self):
  self.assertEqual(self.run_case([(0,b'{"ok":true}',b'')]),(0,b'{"ok":true}',b'',1))
 def test_transport_retry_discards_partial_json(self):
  self.assertEqual(self.run_case([(1,b'partial',b'dial tcp: network is unreachable'),(0,b'{"ok":true}',b'')]),(0,b'{"ok":true}',b'lab-scanner-transport-retries=1\n',2))
 def test_policy_failure_not_retried(self):
  self.assertEqual(self.run_case([(2,b'partial',b'vulnerability policy denied')]),(2,b'',b'vulnerability policy denied',1))
 def test_six_attempt_limit(self):
  status,out,error,count=self.run_case([(1,b'partial',b'dial tcp: network is unreachable')]);self.assertEqual((status,out,count),(1,b'',6))
 def test_total_deadline(self):
  clock=iter((0,0,901,901));calls=[];out=io.BytesIO();err=io.BytesIO()
  def runner(command,**kw):calls.append(command);return subprocess.CompletedProcess(command,1,stderr=b'dial tcp: i/o timeout')
  result=module.scan([],runner=runner,monotonic=lambda:next(clock),pause=lambda _:None,output=out,errors=err)
  self.assertEqual(result,1);self.assertEqual(len(calls),1)
 def test_timeout_not_retried(self):
  calls=[];out=io.BytesIO();err=io.BytesIO()
  def runner(command,**kw):calls.append(command);raise subprocess.TimeoutExpired(command,kw['timeout'])
  self.assertEqual(module.scan([],runner=runner,monotonic=lambda:0,pause=lambda _:None,output=out,errors=err),1);self.assertEqual(len(calls),1);self.assertEqual(out.getvalue(),b'')
if __name__=='__main__':unittest.main()
