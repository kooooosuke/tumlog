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
import re
import simplejson
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import urlfetch

#数字を渡すと曜日を返す。datetime.weekday()と対応
def get_weekdaysJPname(n):
  if n==0:
    return u'月'
  elif n==1:
    return u'火'
  elif n==2:
    return u'水'
  elif n==3:
    return u'木'
  elif n==4:
    return u'金'
  elif n==5:
    return u'土'
  elif n==6:
    return u'日'
  else:
    return 'error'

def storePostDataToDB(acount, n):
    #データをDBから削除
    #db.delete(db.GqlQuery("SELECT * FROM Log_table").fetch(1000))
    num=50
    for i in range(n):
      #time.sleep(0.2)
      #tumblr API叩く
      url = 'http://'+ acount +'.tumblr.com/api/read?num='+ str(num) +'&start='+ str(i*num)
      soup = BeautifulSoup.BeautifulSoup(urllib.urlopen(url))
      ##### postに対する処理 ####
      for post in soup.findAll('post'):
        log_table = Log_table()
        log_table.post_date=datetime.datetime.strptime(post.get('date-gmt'), "%Y-%m-%d %H:%M:%S %Z")
        #UCTから日本時間への変換
        log_table.post_date=log_table.post_date+datetime.timedelta(hours=9)
        log_table.post_id=post.get('id')
        log_table.post_username=acount
        #post type 別に log_table.content 記述内容抽出
        if   post.get('type')=='photo':
          log_table.content='<img src="'+post('photo-url')[5].renderContents()+'" align="top"/>'
        elif post.get('type')=='quote':
          log_table.content=re.compile(r'&lt;.*?&gt;').sub('', post('quote-text')[0].renderContents().decode('utf-8'))[0:140]
        elif post.get('type')=='regular':
          log_table.content=re.compile(r'&lt;.*?&gt;').sub('', post('regular-body')[0].renderContents().decode('utf-8'))[0:140]
        elif post.get('type')=='link':
          log_table.content=re.compile(r'&lt;.*?&gt;').sub('', post('link-text')[0].renderContents().decode('utf-8'))[0:140]
        elif post.get('type')=='conversation':
          log_table.content=re.compile(r'&lt;.*?&gt;').sub('', post('conversation-text')[0].renderContents().decode('utf-8'))[0:140]
        elif post.get('type')=='video':
          if len(post('video-caption'))==0:
            log_table.content=re.compile(r'&lt;.*?&gt;').sub('', post('video-source')[0].renderContents().decode('utf-8'))[0:140]
          else :
            log_table.content=re.compile(r'&lt;.*?&gt;').sub('', post('video-caption')[0].renderContents().decode('utf-8'))[0:140]
        elif post.get('type')=='audio':
          log_table.content=re.compile(r'&lt;.*?&gt;').sub('', post('audio-caption')[0].renderContents().decode('utf-8'))[0:140]
        #重複チェック
        duplication=db.GqlQuery("SELECT * FROM Log_table WHERE post_id='"+log_table.post_id+"'").count()
        if duplication>0:
         continue
        #DBに格納
        log_table.put()

#DB定義
class Log_table(db.Model):
  post_date = db.DateTimeProperty()
  post_id = db.StringProperty()
  post_username = db.StringProperty()
  content = db.StringProperty(multiline=True)

#/     フォームからacount取得
class MainPage(webapp.RequestHandler):
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, 0))

#/log/     acountを受け取ってViewにリダイレクトするだけ
class Log(webapp.RequestHandler):
  def post(self):
    acount=self.request.get('acount')
    self.redirect('/log/'+acount)
    
#/datastore     acountを受け取ってデータ更新してViewにリダイレクト
class Datastore(webapp.RequestHandler):
  def post(self):
    acount=self.request.get('acount')
    storePostDataToDB(acount, 10)
    self.redirect('/log/'+acount)

#/ultimetdatastore     acountを受け取ってたくさんデータ更新してViewにリダイレクト
class UltimetDatastore(webapp.RequestHandler):
  def post(self):
    acount=self.request.get('acount')
    json_url='http://api.tumblr.com/v2/blog/'+acount+'.tumblr.com/info?api_key=IqGv9kCiX4nU2r7XFyiAkIz7VI0a4MrQcJ8hPWKKN6yHSK1pLh'
    json_data=simplejson.load(urllib2.urlopen(json_url), encoding='utf8')
    max=int(json_data['response']['blog']['posts'])
    storePostDataToDB(acount, max/50+1)
    self.redirect('/log/'+acount)

#/log/****     ログ表示
class View(webapp.RequestHandler):
  def get(self, page):
    acount=page
    
    ##### 時間帯/曜日ごとのpost割合を算出 #####
    #初期化
    hours=[]
    hours_rate=[]
    for i in range(24):
      hours.append(0.0)#double
    weekdays=[]
    weekdays_rate=[]
    for i in range(7):
      weekdays.append(0.0)#double
    #算出
    post_logs=db.GqlQuery("SELECT * FROM Log_table WHERE post_username = '"+acount+"' ORDER BY post_date DESC LIMIT 999999")
    totoal_stored_post_num=post_logs.count(999999)
    for log in post_logs:
      hours[int(log.post_date.hour)]=hours[int(log.post_date.hour)]+1.0
      weekdays[int(log.post_date.weekday())]=weekdays[int(log.post_date.weekday())]+1.0
    for (hour, i) in zip(hours, range(24)):
      hours_rate.append(str(i)+u"時 "+str(hour*100/(totoal_stored_post_num+0.00000000001))[0:4]+"%")#zero division
    for (weekday, i) in zip(weekdays, range(7)):
      weekdays_rate.append(get_weekdaysJPname(i)+u"曜日 "+str(weekday*100/(totoal_stored_post_num+0.00000000001))[0:4]+"%")
    for i in range(10):
      hours_rate[i]='0'+hours_rate[i]

    
    ##### 日ごとのpost数を算出 #####
    today=datetime.datetime.now()
    today=today+datetime.timedelta(hours=9)
    nextday=today+datetime.timedelta(days=1)
    recent_daily_posts=[]
    # myposts = db.GqlQuery("SELECT * FROM Log_table WHERE post_username = '"+acount+"'")
    for i in range(14):
      query="SELECT * FROM Log_table WHERE post_username = '"+acount+"' AND post_date>=datetime("+str(today.year)+", "+str(today.month)+", "+str(today.day)+") AND post_date<datetime("+str(nextday.year)+", "+str(nextday.month)+", "+str(nextday.day)+")"
      daily_posts = db.GqlQuery(query)
      recent_daily_post={"count":daily_posts.count(), "date":str(today.year)+"/"+str(today.month)+"/"+str(today.day)}
      recent_daily_posts.append(recent_daily_post)
      today=today-datetime.timedelta(days=1)
      nextday=nextday-datetime.timedelta(days=1)
    ##### 月ごとのpost数を算出 #####    
    today=datetime.datetime.now()
    today=today+datetime.timedelta(hours=9)
    nextday=today+datetime.timedelta(days=1)
    recent_monthly_posts=[]
    for i in range(12):
      if today.month-i > 0:
        query="SELECT * FROM Log_table WHERE post_username = '"+acount+"' AND post_date>=datetime("+str(today.year)+", "+str(today.month-i)+", 1) AND post_date<datetime("+str(today.year)+", "+str(today.month-i+1)+", 1)"
        monthly_posts = db.GqlQuery(query)
        recent_monthly_post={"count":monthly_posts.count(), "date":str(today.year)+"/"+str(today.month-i)}
      elif today.month-i == 0:
        query="SELECT * FROM Log_table WHERE post_username = '"+acount+"' AND post_date>=datetime("+str(today.year-1)+", "+str(today.month-i+12)+", 1) AND post_date<datetime("+str(today.year)+", "+str(today.month-i+1)+", 1)"
        monthly_posts = db.GqlQuery(query)
        recent_monthly_post={"count":monthly_posts.count(), "date":str(today.year-1)+"/"+str(today.month-i+12)}
      else :
        query="SELECT * FROM Log_table WHERE post_username = '"+acount+"' AND post_date>=datetime("+str(today.year-1)+", "+str(today.month-i+12)+", 1) AND post_date<datetime("+str(today.year-1)+", "+str(today.month-i+12+1)+", 1)"
        monthly_posts = db.GqlQuery(query)
        recent_monthly_post={"count":monthly_posts.count(), "date":str(today.year-1)+"/"+str(today.month-i+12)}
      recent_monthly_posts.append(recent_monthly_post)
    
    ##### ユーザー名・ブログタイトル ####
    json_url='http://api.tumblr.com/v2/blog/'+acount+'.tumblr.com/info?api_key=******************************************'
    json_data=simplejson.load(urllib2.urlopen(json_url), encoding='utf8')
    ##### アバター #####
    avatar_img_src_url='http://api.tumblr.com/v2/blog/'+acount+'.tumblr.com/avatar/30'
    
    
    
    template_values={
      'log_tables':post_logs.fetch(30), #最新30件だけ表示
      'recent_daily_posts':recent_daily_posts,#最近の日ごとのpost数比率
      'recent_monthly_posts':recent_monthly_posts,#最近の月ごとのpost数比率
      'hours_rate':hours_rate,             #時間ごとのpost数比率
      'weekdays_rate':weekdays_rate, #曜日ごとのpost数比率
      'j':json_data,                              #blogデータ
      'avatar':avatar_img_src_url,        #ユーザーのアイコン画像
      'totoal_stored_post_num':totoal_stored_post_num
    }
    path = os.path.join(os.path.dirname(__file__), 'log.html')
    self.response.out.write(template.render(path, template_values))
    




#URL mapping
application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/log', Log),
                                      (r'/log/(.*)', View),
                                      ('/datastore', Datastore),
                                      ('/ultimetdatastore', UltimetDatastore)],
                                     debug=True)

#omajinai
def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
