
# A very simple Flask Hello World app for you to get started with...

from flask import Flask, request, redirect, session, jsonify
import os
from flask_cors import CORS, cross_origin
from breeze_connect import BreezeConnect
from datetime import datetime

app = Flask(__name__)
cors = CORS(app)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['CORS_HEADERS'] = 'Content-Type'
app.secret_key = "939C6l37E=53245%5i930lJa4)B60u60"

breeze = BreezeConnect(api_key="$6Y56)71761r28t23V2751~dQ7j8o518")


#@app.after_request
#def after_request(response):
#    header = response.headers
#    header['Access-Control-Allow-Origin'] = '*'
    # Other headers can be added here if needed
#    return response

if __name__ == '__main__':
	app.run(debug = True)


@app.route('/', methods=['GET', 'POST'])
@cross_origin()
def apiSessionFromBreezeApi():
    queryParams = request.args.to_dict()
    apiSession = queryParams.get('apisession','no-breezeapi-session')
    session["apisession"] = apiSession
    try:
        file_path = './bzapisessions/'+apiSession
        # create file
        with open(file_path, 'x') as fp:
            fp.close()
    except:
        print('File already exists')

    breeze.generate_session(api_secret=app.secret_key,session_token=apiSession)
    breeze.ws_connect()
    return apiSession
    #return redirect("/oneclick", code=302)

@app.route('/getExistingSessions', methods=['GET', 'POST'])
@cross_origin()
def getExistingSessions():
    existingSession = os.listdir('./bzapisessions')
    outputResponse = "{\"msg\" : \"Existing api sessions=" + str(existingSession) + "\"}"
    return (outputResponse,200, {'Content-Type': 'application/json'})

@app.route('/getCurrentSession', methods=['GET', 'POST'])
@cross_origin()
def getCurrentSession():
    return session["apisession"]

@app.route('/clearSessionFiles', methods=['GET', 'POST'])
@cross_origin()
def clearSessionFiles():
    queryParams = request.args.to_dict()
    apiSession = queryParams.get('sessionfile','none')
    if apiSession != "none":
        if os.path.exists("./breezeapi/bzapisessions/" + apiSession):
            os.remove("./breezeapi/bzapisessions/" + apiSession)
    return redirect("/getExistingSessions", code=302)

@app.route('/getCustomerDetails', methods=['GET', 'POST'])
@cross_origin()
def getCustomerDetails():
    customerDetails = breeze.get_customer_details(api_session=session["apisession"])
    return (customerDetails,200, {'Content-Type': 'application/json'})

@app.route('/getQuotes', methods=['GET', 'POST'])
@cross_origin()
def getQuotes():
    quotes = breeze.get_quotes("CNXBAN","NFO","2023-09-28T06:00:00.000Z","Futures","Others","0")
    return (quotes,200, {'Content-Type': 'application/json'})

@app.route('/orderList', methods=['GET', 'POST'])
@cross_origin()
def getOrderList():
    from_date = datetime.strpdate(str(datetime.today()),"%Y-%m-%d").isoformat()[:10] + 'T05:30:00.000Z'
    to_date = datetime.strpdate(str(datetime.today()),"%Y-%m-%d").isoformat()[:10] + 'T20:30:00.000Z'

    return breeze.get_order_list(exchange_code="NFO",
                        from_date=from_date,
                        to_date=to_date)