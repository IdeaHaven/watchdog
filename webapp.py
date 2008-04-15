#!/usr/bin/python
import os, re
import web
from utils import zip2rep, simplegraphs, apipublish
import blog

web.config.debug = True
web.template.Template.globals['commify'] = web.commify
render = web.template.render('templates/', base='base')
db = web.database(dbn=os.environ.get('DATABASE_ENGINE', 'postgres'), db='watchdog_dev')

options = r'(?:\.(html|xml|rdf|n3|json))'
urls = (
  r'/', 'index',
  r'/us/(?:index%s)?' % options, 'find',
  r'/us/([A-Z][A-Z])', 'redistrict',
  r'/us/([a-z][a-z])%s?' % options, 'state',
  r'/us/([A-Z][A-Z]-\d+)', 'redistrict',
  r'/us/([a-z][a-z]-\d+)%s?' % options, 'district',
  r'/us/by/(.*)/distribution.png', 'sparkdist',
  r'/us/by/(.*)', 'dproperty',
  r'/p/(.*?)%s?' % options, 'politician',
  r'/about(/?)', 'about',
  r'/about/feedback', 'feedback',
  r'/blog', 'reblog',
  r'/blog(/.*)', blog.app,
  r'/data/(.*)', 'staticdata'
)

class index:
    def GET(self):
        return render.index()

class about:
    def GET(self, endslash=None):
        if not endslash: raise web.seeother('/about/')
        return render.about()

class feedback:
    def GET(self):
        raise web.seeother('/about')
    
    def POST(self):
        i = web.input(email='info@watchdog.net')
        web.sendmail('Feedback <%s>' % i.email, 'Watchdog <info@watchdog.net>',
          'watchdog.net feedback', 
          i.content +'\n\n' + web.ctx.ip)
        
        return render.feedback_thanks()

class reblog:
    def GET(self):
        raise web.seeother('/blog/')

class find:
    def GET(self, format=None):
        i = web.input(address=None)
        if i.get('zip'):
            try:
                dists = zip2rep.zip2dist(i.zip, i.address)
            except zip2rep.BadAddress:
                return render.find_badaddr(i.zip, i.address)
            if len(dists) == 1:
                raise web.seeother('/us/%s' % dists[0].lower())
            elif len(dists) == 0:
                return render.find_none(i.zip)
            else:
                dists = db.select(['district' + ' LEFT OUTER JOIN politician ON (politician.district = district.name)'], where=web.sqlors('name=', dists))
                return render.find_multi(i.zip, dists)
        else:
            out = apipublish.publish([{
              'uri': 'http://watchdog.net/us/' + x.name.lower(),
              'type': 'District',
              'name': x.name,
              'state': x.state,
              'district': x.district,
              'voting': x.voting,
              'wikipedia': apipublish.URI(x.wikipedia)
             } for x in db.select('district')], format)
            if out is not False:
                return out
            
            dists = db.select(['district' + ' LEFT OUTER JOIN politician ON (politician.district = district.name)'], order='name asc')
            return render.districtlist(dists)

class state:
    def GET(self, state, format=None):
        state = state.upper()
        try:
            state = db.select('state', where='code=$state', vars=locals())[0]
        except IndexError:
            raise web.notfound
        
        out = apipublish.publish([{
          'uri': 'http://watchdog.net/us/' + state.code.lower(),
          'type': 'State',
          'code': state.code,
          'fipscode': state.fipscode,
          'name': state.name,
          'status': state.status,
          'wikipedia': apipublish.URI(state.wikipedia)
         }], format)
        if out is not False:
            return out
        
        districts = db.select('district', where='state=$state.code', order='district asc', vars=locals())
        
        return render.state(state, districts.list())

class redistrict:
    def GET(self, district):
        return web.seeother('/us/' + district.lower())

class district:
    def GET(self, district, format=None):
        try:
            district = district.upper()
            d = db.select(['district', 'state', 'politician'], what='district.*, state.name as state_name, politician.firstname as pol_firstname, politician.lastname as pol_lastname, politician.id as pol_id, politician.photo_path as pol_photo_path', where='district.name = $district AND district.state = state.code AND politician.district = district.name', vars=locals())[0]
        except IndexError:
            raise web.notfound
        
        out = apipublish.publish([{
          'uri': 'http://watchdog.net/us/' + district,
          'type': 'District',
          'name': d.name,
          'state': apipublish.URI('http://watchdog.net/us/' + d.state.lower()),
          'voting': d.voting,
          'wikipedia': apipublish.URI(d.wikipedia),
          'almanac': apipublish.URI(d.almanac),
          'area_sqmi': d.area_sqmi,
          'cook_index': d.cook_index,
          'poverty_pct': d.poverty_pct,
          'median_income': d.median_income,
          'est_population': d.est_population,
          'est_population_year': d.est_population_year,
          'outline': d.outline,
          'center_lat': d.center_lat,
          'center_lng': d.center_lng,
          'zoom_level': d.zoom_level
         }], format)
        if out is not False:
            return out
        
        if d.district == 0:
            d.districtth = 'at-large'
        elif str(d.district).endswith('1'):
            d.districtth = '%sst' % d.district
        elif str(d.district).endswith('2'):
            d.districtth = '%snd' % d.district
        elif str(d.district).endswith('3'):
            d.districtth = '%srd' % d.district
        else:
            d.districtth = '%sth' % d.district
        
        return render.district(d)

class politician:
    def GET(self, polid, format=None):
        if polid != polid.lower():
            raise web.seeother('/p/' + polid.lower())
        
        try:
            p = db.select(['politician', 'district'], what="politician.*, district.center_lat as d0, district.center_lng as d1, district.zoom_level as d2", where='id=$polid AND district.name = politician.district', vars=locals())[0]
        except IndexError:
            raise web.notfound
        
        out = apipublish.publish([{
          'uri': 'http://watchdog.net/p/' + polid,
          'type': 'Politician',
          'district': apipublish.URI('http://watchdog.net/us/' + p.district.lower()),
          'wikipedia': apipublish.URI(p.wikipedia),
          'bioguideid': p.bioguideid,
          'opensecretsid': p.opensecretsid,
          'govtrackid': p.govtrackid,
          'gender': p.gender,
          'birthday': p.birthday,
          'firstname': p.firstname,
          'middlename': p.middlename,
          'lastname': p.lastname,
          'officeurl': p.officeurl,
          'party': p.party,
          'religion': p.religion,
          'photo_path': p.photo_path,
          'photo_credit_url': p.photo_credit_url,
          'photo_credit_text': p.photo_credit_text,
         }], format)
        if out is not False:
            return out
        
        return render.politician(p)

r_safeproperty = re.compile('^[a-z0-9_]+$')

class dproperty:
    def GET(self, what):
        if not r_safeproperty.match(what): raise web.notfound
        
        maxnum = float(db.select('district', what='max(%s) as m' % what, vars=locals())[0].m)
        dists = db.select('district', what="*, 100*(%s/$maxnum) as pct" % what, order='%s desc' % what, where='%s is not null' % what, vars=locals())
        return render.dproperty(dists, what)

class sparkdist:
    def GET(self, what):
        if not r_safeproperty.match(what): raise web.notfound
        
        inp = web.input(point=None)
        points = db.select('district', what=what, order=what+' desc', where=what+' is not null')
        points = [x[what] for x in points.list()]
        
        web.header('Content-Type', 'image/png')
        return simplegraphs.sparkline(points, inp.point)

class staticdata:
    def GET(self, path):
        if not web.config.debug:
            raise web.notfound

        assert '..' not in path, 'security'
        return file('data/' + path).read()

app = web.application(urls, globals())
if __name__ == "__main__": app.run()
