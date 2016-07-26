from flask import Blueprint, request, session, redirect, render_template, url_for
from requests_oauthlib import OAuth2Session
import yaml, requests, json
from services_util import *

config = yaml.load(open('services.conf', 'r'))

OAUTH2_CLIENT_ID = config['OAUTH2_CLIENT_ID']
OAUTH2_CLIENT_SECRET = config['OAUTH2_CLIENT_SECRET']
OAUTH2_REDIRECT_URI = config['OAUTH2_REDIRECT_URI']

API_BASE_URL = 'https://discordapp.com/api'
AUTHORIZATION_BASE_URL = API_BASE_URL + '/oauth2/authorize'
TOKEN_URL = API_BASE_URL + '/oauth2/token'

WDS_CORP_ID = "98330748"
ACADEMY_CORP_ID = "98415327"

if 'http://' in OAUTH2_REDIRECT_URI:
  os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

services_discord = Blueprint('services_discord', __name__)

@services_discord.route('/discordauth')
def discordauth():
  """
  Method creates authorized discord session, 
  sets auth state and redirects to authed url.
  """
  scope = request.args.get(
      'scope',
      'identify email')
  discord = make_session(scope=scope.split(' '))
  authorization_url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
  session['oauth2_state'] = state
  return redirect(authorization_url)

@services_discord.route('/callback')
def callback():
  """
  Method sets OAuth2 session token, otherwise returns an error.
  """
  if request.values.get('error'):
    return request.values['error']
  discord = make_session(state=session.get('oauth2_state'))
  token = discord.fetch_token(
    TOKEN_URL,
    client_secret = OAUTH2_CLIENT_SECRET,
    authorization_response=request.url)
  session['oauth2_token'] = token
  return redirect(url_for('.authme'))

@services_discord.route('/authme')
def authme():
  """
  Method validates pilot email, if account is active/incorp and updates
  DB with discord ID and pushes new member to discord API.
  """
  ACADEMY_ROLE_ID = '172888937453322240'
  AGENT_ROLE_ID = '172888812991676416'

  discord = make_session(token=session.get('oauth2_token'))
  user = discord.get(API_BASE_URL + '/users/@me').json()
 
  email = user['email']
  validated = user['verified']
  discordid = user['id']
 
  #app 500s if email doesn't exist
  if not email: #or not validated or not discordid:
    print("failed due to blank email")
    return render_template('services-discord-error.html')
  
  #app 500s if email account not validated
  if not validated: #or not validated or not discordid:
    print("failed to auth {email} due to unvalidated account".format(email=email))
    return render_template('services-discord-error.html')

  #app 500s if discordid is blank
  if not discordid: #or not validated or not discordid:
    print("failed to auth {email} due to blank discordid".format(email=email))
    return render_template('services-discord-error.html')
  
  #check that the email address is valid, the account is active and in corp
  valid_user_query = query_db('SELECT email FROM pilots '
                              'WHERE active_account=1 '
                              'AND in_alliance=1 ' 
                              'AND lower(email) = ? '
                              'LIMIT 1', [email.lower()])
  
  if len(valid_user_query) == 1 and validated:
    #update the pilots record with their discord id
    update_query = insert_db('UPDATE pilots '
                             'SET discordid=? '
                             'WHERE lower(email) = ?', [discordid, email.lower()])
    #check if the pilot is in maincorp
    corp = which_corp(email)

    if not corp:
      print("couldn't determine users corp.  Probably an expired key: {email}".format(email=email))
      return render_template('services-discord-error.html')

    data = ""

    if corp == WDS_CORP_ID:
      data = AGENT_ROLE_ID
    elif corp == ACADEMY_CORP_ID:
      data = ACADEMY_ROLE_ID
	 
    #push a request to the discord api endpoint
    headers = {'user-agent': 'WiNGSPAN External Auth/0.1', 'authorization' : BOT_TOKEN}
    uri = '{base}/guilds/{guildid}/members/{discordid}'.format(base = API_BASE_URL,
                                                               guildid = GUILD_ID,
                                                               discordid = discordid)
    req = requests.patch(uri, json = {'roles':[data]}, headers = headers)

    return render_template('services-discord-success.html')

  else:
    print('{email} failed to auth'.format(email = email))
    return render_template('services-discord-error.html')

def make_session(token=None, state=None, scope=None):
  """
  Method creates OAuth2 session providing the token, state, and scope.
  Returns OAuth 2 Session Object
  """
  return OAuth2Session(
      client_id=OAUTH2_CLIENT_ID,
      token=token,
      state=state,
      scope=scope,
      redirect_uri=OAUTH2_REDIRECT_URI,
      auto_refresh_kwargs={

        'client_id': OAUTH2_CLIENT_ID,
        'client_secret': OAUTH2_CLIENT_SECRET,
      },
      auto_refresh_url=TOKEN_URL,
      token_updater=token_updater)

def token_updater(token):
  """
  Method updates OAuth2 token.
  """
  session['oauth2_token'] = token

