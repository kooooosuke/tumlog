#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib
import urllib2
import BeautifulSoup
import datetime
import time
import locale
import sys
import codecs
import cgi
import os
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import urlfetch

#database declaration
class Log_table(db.Model):
  width  = db.IntegerProperty()
  height = db.IntegerProperty()
  post_url = db.StringProperty()
  img_url = db.StringProperty()

#index.html
class MainPage(webapp.RequestHandler):
  def get(self):
    template_values={'a':1}
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

#log.html
class Guestbook(webapp.RequestHandler):
  def post(self):
    tumblr_email = "subaka25255@yahoo.co.jp"
    tumblr_password = "zaqzaq123"
    #前回のデータをDBから削除
    q = db.GqlQuery("SELECT * FROM Log_table")
    results = q.fetch(1000)
    db.delete(results)
  
    #一度に読み込むpost数
    num=50
    acount=self.request.get('content')
    d = datetime.datetime.today()
    for i in range(2):
      time.sleep(0.2)
      url = 'http://www.tumblr.com/api/dashboard?email='+tumblr_email+'&password='+tumblr_password+'&num='+ str(num) +'&start='+ str(i*num)+'&type=photo'
      req = urllib2.Request(url)
      content = urllib2.urlopen(req).read()
      soup = BeautifulSoup.BeautifulSoup(content)
      #postに対する処理
      for post in soup('post'):
        log_table = Log_table()
        log_table.width=int(post.get('width'))
        log_table.height=int(post.get('height'))
        log_table.post_url=post.get('url')
        log_table.img_url = post('photo-url')[3].renderContents()
        log_table.put()
        
        
        
        
    log_tables_query = Log_table.all()
    log_tables = log_tables_query.fetch(50)
    
    template_values={
      'log_tables':log_tables,
    }
    path = os.path.join(os.path.dirname(__file__), 'log2.html')
    self.response.out.write(template.render(path, template_values))
    




#URL mapping
application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/log', Guestbook)],
                                     debug=True)

#omajinai
def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()