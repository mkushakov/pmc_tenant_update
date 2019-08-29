import requests
import json
import time
import sys

client_id = ''
client_secret = ''
pmc_url = 'https://pmc.beqom.com/'
pmc_tm_url = 'https://pmctm.beqom.com/'
service_id = sys.argv[1]
timeOut = 450

def get_token(client_id, client_secret):
    return requests.post('https://passport.beqom.com/api/auth', json={
        'client_id': client_id,
        'client_secret': client_secret,
        })
def get_tenants(token):
    return requests.get( pmc_tm_url + 'api/TenantUpdate?filters.IsUpdateNeeded=true', headers={
        'Authorization':'bearer ' + token
        })
def tenant_update(token, data):
    return requests.post( pmc_tm_url + 'api/TenantUpdate/Update', json=data, headers={
        'Authorization':'bearer ' + token
    })
def tenant_log(token, tenant):
    return requests.get( pmc_tm_url + 'api/TenantUpdateLog?&filters.TenantUID=' + tenant + '&page=0&pageSize=1', headers={
        'Authorization':'bearer ' + token
        })
def activity_log(token):
    return requests.get(pmc_url + 'api/ActivityLog/GetParents?&filters.Action=Update&page=0&pageSize=10', headers={
        'Authorization':'bearer ' + token
    })
def activlog_status(resp, tenant):
    for a in resp.json()['List']:
        d = json.loads(a['Details'])
        if a['Status'] == 2 and d['TenantCode'] == tenant: return 2
        elif a['Status'] == 3 and d['TenantCode'] == tenant: return 3
        elif a['Status'] == 1 and d['TenantCode'] == tenant: return 1
        else: return 0
def slack_notification(text):
    text = json.dumps(text)
    return requests.post('https://hooks.slack.com/services/', data=text)

# Geting token from Passport
print('Trying to retrive token from Passport...')
resp = get_token(client_id, client_secret)
if resp.status_code != 200:
    raise Exception('Cannot authorize in Passport: {}'.format(resp.status_code))
token = resp.json()['access_token']
print('Token accuried.')

# Creating list of tenant to update
print('Calling PMC-TM to get list of tenants to update...')
resp = get_tenants(token)
tenants = []
if resp.status_code != 200:
    raise Exception('Cannot get tenants list from PMC: {} {}'.format(resp.status_code, resp.json()))
print('PMC-TM responded with a list.')
for t in resp.json()['List']:
    if t['Tenant']['CloudServiceID'] == service_id:
        tenant = {}
        tenant.update({'ID': t['Tenant']['ID']}) 
        tenant.update({'Code': t['Tenant']['Code']}) 
        tenant.update({'DbVersion': t['Tenant']['DbVersion']})
        tenant.update({'TargetVersion': t['LatestVersion']})
        tenants.append(tenant)
print('Tenant list generted.')

# Updating tenant
print('Starting tenant update...')
for item in tenants:
    data = [{'ID': item['ID'], 'FromVersion': item['DbVersion'], 'ToVersion': item['TargetVersion']}]
    resp = tenant_update(token, data)
    if resp.status_code != 204:
        raise Exception('Cannot update tenant in PMC: {} {}'.format(resp.status_code, resp.text))
    print('Request to update send to PMC for tenant {}'.format(item['Code']))

    # Get Activity Log
    resp = activity_log(token)
    if resp.status_code != 200:
        raise Exception('Cannot get activity logs: {} {}'.format(resp.status_code, resp.text))
    print('Activity log requested')
    
    # Get status
    print('Requesting Status for {} update...'.format(item['Code']))
    stat = activlog_status(resp, item['Code'])
    i = 0
    while stat == 1 or stat == 0:
        i += 1
        time.sleep(2)
        resp = activity_log(token)
        stat = activlog_status(resp, item['Code']) 
        if resp.status_code != 200:
            raise Exception('Cannot get activity logs in the loop: {} {}'.format(resp.status_code, resp.text))
        if i > timeOut:
            print('Timeing out after {} seconds for tenant {}'.format(timeOut*2, item['Code']))
            text = {'attachments': [{
                'color': 'warning',
                'author_name': 'PMC autoupdater function',
                'title_link': pmc_url + '#/appversion-tenant-logs?tenantId=' + item['ID'],
                'title': item['Code'],
                'text': 'Timing out to update tenant to version *{}*'.format(item['TargetVersion'])
                }]}
            r = slack_notification(text)
            break
    if stat == 3:
        print('Failed to update tenant {}'.format(item['Code']))
        text = {'attachments': [{
            'color': 'danger',
            'author_name': 'PMC autoupdater function',
            'title_link': pmc_url + '#/appversion-tenant-logs?tenantId=' + item['ID'],
            'title': item['Code'],
            'text': 'Failed to update tenant to version *{}*'.format(item['TargetVersion'])
            }]}
        r = slack_notification(text)
    else:
        print('Tenant {} has been update'.format(item['Code']))
        text = {'attachments': [{
            'color': 'good',
            'author_name': 'PMC autoupdater function',
            'title_link': pmc_url + '#/appversion-tenant-logs?tenantId=' + item['ID'],
            'title': item['Code'],
            'text': 'Tenant has been update to version *{}*'.format(item['TargetVersion'])
            }]}
        r = slack_notification(text)
