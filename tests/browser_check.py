"""Optional Chrome/Chromium browser acceptance on the target laptop. Uses a throwaway database."""
import os,sys,socket,shutil,subprocess,tempfile,time,urllib.request
from pathlib import Path
def main():
    from playwright.sync_api import sync_playwright
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        url=f'http://127.0.0.1:{port}'
        env={**os.environ,'WELFARE_DATA':tmp}
        server=subprocess.Popen([sys.executable,'-c',"import sys;sys.path.insert(0,'tests');import unit_database,navigator.mysql_store;navigator.mysql_store.Database=unit_database.UnitDatabase;from run import main;main()",'--no-browser','--port',str(port)],cwd=root,env=env,stdout=subprocess.DEVNULL)
        try:
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            for i in range(60):
                try:opener.open(url,timeout=1).close();break
                except OSError:time.sleep(.25)
            with sync_playwright() as pw:
                binary=os.getenv('CHROMIUM_PATH') or shutil.which('chromium')
                browser=pw.chromium.launch(executable_path=binary or None,headless=True)
                page=browser.new_page(viewport={'width':1360,'height':950});errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(url);page.locator('.hero').wait_for()
                page.goto(url+'/#family');page.locator('#registerfamily').click()
                page.locator('#issuedcode').wait_for();page.locator('#familylogin button').click();page.locator('#create').wait_for()
                page.goto(url+'/#home');page.locator('.hero').wait_for()
                page.locator('#find').fill('PM-KISAN');page.locator('#searchform button').click();page.locator('#catalogue .card').first.wait_for()
                assert page.locator('#catalogue .card').count()==1
                page.goto(url+'/#family');page.locator('#demoPerson').select_option('1');page.locator('#consent').check();page.locator('#create').click();page.locator('.member').first.wait_for()
                for route in ['home','guide/ayushman','check/ayushman','explore','family','compare','simulate/ayushman','docs/ayushman','scan','draft/ayushman','apps','centres','alerts','report']:
                    page.goto(url+'/#'+route);page.wait_for_timeout(125);assert page.locator('main h1').count()>0,route;assert not page.locator('#errors:visible').count(),route
                page.goto(url+'/#draft/ayushman');page.locator('#form0').fill('Demo Senior');page.locator('#savework').click();page.locator('#saved .notice').wait_for()
                page.goto(url+'/#apps');page.get_by_text('Documents pending',exact=True).first.wait_for()
                page.goto(url+'/#admin');page.locator('#password').fill((Path(tmp)/'ADMIN_FIRST_LOGIN.txt').read_text().strip());page.locator('#loginform button').click();page.locator('#adminpage').wait_for()
                for route in ['manage','kb','monitor','experiments','analytics','logs','privacy','settings']:
                    page.locator('#adminpage').select_option(route);page.wait_for_function('location.hash === "#'+route+'"');page.wait_for_timeout(200);assert page.locator('#adminbody h2,#adminbody textarea,#adminbody .stat').count()>0,route
                page.set_viewport_size({'width':390,'height':844});page.goto(url+'/#home');page.locator('.hero').wait_for()
                for lang in ['te','hi','en']:
                    page.locator('#language').select_option(lang);page.wait_for_function('document.documentElement.lang === "'+lang+'"')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+2'),lang
                assert not errors,errors
                browser.close();print('PASS: 22 sections, draft persistence, login, three mobile languages.')
        finally:server.terminate();server.wait(timeout=10)
if __name__=='__main__':main()
