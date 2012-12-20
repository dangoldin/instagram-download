import bottle
from bottle import route, post, run, request
from instagram import client, subscriptions
import urllib

bottle.debug(True)

CONFIG = {
    'client_id': '540ac239ceb24cccbe821198901f058d',
    'client_secret': '65bdaf2ead2041e4a1bfc88332daaafb',
    'redirect_uri': 'http://localhost:8515/oauth_callback'
}

unauthenticated_api = client.InstagramAPI(**CONFIG)

def process_tag_update(update):
    print update

reactor = subscriptions.SubscriptionsReactor()
reactor.register_callback(subscriptions.SubscriptionType.TAG, process_tag_update)

def get_photos(access_token, max_id = None):
    api = client.InstagramAPI(access_token=access_token)
    if max_id is not None:
        user_media, next = api.user_recent_media(count=50, max_id=max_id)
    else:
        user_media, next = api.user_recent_media(count=50)
    return user_media

@route('/')
def home():
    try:
        url = unauthenticated_api.get_authorize_url(scope=["likes","comments"])
        return '<a href="%s">Connect with Instagram</a>' % url
    except Exception, e:
        print e

@route('/download')
def download():
    access_token = request.GET.get('access_token')
    photos = []
    max_id = None
    while True:
        print 'Getting photos with max id: %s' % str(max_id)
        user_media = get_photos(access_token=access_token, max_id = max_id)
        for media in user_media:
            urllib.urlretrieve(media.images['standard_resolution'].url, '%s.jpg' % media.id)
            photos.append('<img src="%s"/>' % media.images['thumbnail'].url)
        if len(user_media) == 0:
            break
        max_id = user_media[-1].id
    return 'Retrieved %d photos<br/>' % len(photos) + ''.join(photos)

@route('/oauth_callback')
def on_callback():
    code = request.GET.get("code")
    if not code:
        return 'Missing code'
    try:
        access_token_result = unauthenticated_api.exchange_code_for_access_token(code)
        access_token = access_token_result[0]
        if not access_token:
            return 'Could not get access token'
        
        return 'Your access token is %s.<br/>Click <a href="/download?access_token=%s">here</a> to download your photos (may take a while).' % (access_token, access_token)
    except Exception, e:
        print e

@route('/realtime_callback')
@post('/realtime_callback')
def on_realtime_callback():
    mode = request.GET.get("hub.mode")
    challenge = request.GET.get("hub.challenge")
    verify_token = request.GET.get("hub.verify_token")
    if challenge: 
        return challenge
    else:
        x_hub_signature = request.header.get('X-Hub-Signature')
        raw_response = request.body.read()
        try:
            reactor.process(CONFIG['client_secret'], raw_response, x_hub_signature)
        except subscriptions.SubscriptionVerifyError:
            print "Signature mismatch"

run(host='localhost', port=8515, reloader=True)