
import urllib.request 
import os, zipfile, gzip, shutil
from datetime import datetime
import pandas as pd



directory_path = "./instruments"

def __init__(self, broker):
    print("Instruments class initialized")

def downloadFile(url, filename):
    if not os.path.isfile(filename):
        print("Downloading from " + url + " to " + filename)
        urllib.request.urlretrieve(url, filename)
    else:
        print("File with similar name exists. Skipping file download: " + filename)

def clearOldFiles():
    
    try:
        files = os.listdir(directory_path)
        for file in files:
            file_path = os.path.join(directory_path, file)
            if os.path.isfile(file_path):
                fileCreateTimestamp = os.path.getctime(file_path)
                fileCreateTimeDate = datetime.fromtimestamp(fileCreateTimestamp).date()
                today = datetime.now().date()
			    #print(today - securityMasterCreateTimeDate)
                if today > fileCreateTimeDate:
                    os.remove(file_path)
                else:
                    raise Exception("Files are recent. Delete manually to download again.")
        print("All files deleted successfully.")
    except Exception as e:
        print("Error occurred while deleting files.")
        print(e)
        #raise e
    
def unzipFiles():
    """Unzips all zip files in the given directory."""
    directory = directory_path
    print("Unzipping files in " + directory)
    for filename in os.listdir(directory):
        if filename.endswith(".zip") :
            filepath = os.path.join(directory, filename)
            print("unzipping " + filepath)
            with zipfile.ZipFile(filepath, 'r') as zip_ref:               
                try:
                    zip_ref.extractall(directory)
                except Exception as e:
                    print("Error occurred while deleting files.")
                    print(e)
        if filename.endswith(".gz") :
            filepath = os.path.join(directory, filename)
            print("unzipping " + filepath)
                     
            try:
                file_name = (os.path.basename(filepath)).rsplit('.',1)[0] #get file name for file within
                file_name = os.path.join(directory, file_name)
                print("unzipping to file " + file_name)
                with gzip.open(filepath,"rb") as f_in, open(file_name,"wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)   
            except Exception as e:
                print("Error occurred while unzipping files.")
                print(e)

def readFiles():
    try:
        

        print("Reading unzippped files")
        selectedColumns_idirect = ['Token','InstrumentName','ShortName','Series','ExpiryDate',
            'StrikePrice','OptionType','LotSize','CompanyName','ExchangeCode','ExAllowed']
        df = pd.read_csv(directory_path + '/FONSEScripMaster.txt',header=0,usecols=selectedColumns_idirect)
        df = df.rename(columns={'Token':'idirect_id'})
        indexOnly = df["InstrumentName"].str.contains("FUTIDX") | df["InstrumentName"].str.contains("OPTIDX")
        mask = indexOnly
        df_filtered_idirect = df.loc[mask]
        df_filtered_idirect.to_csv(directory_path + '/idirect-filtered.csv', index=False)
        print(df_filtered_idirect.head()) 

        print("Reading unzippped files")
        selectedColumns_idirect_orig = ['SC','SN','EC','SM','SG',
            'TK','LS','CD','NS','TS']
        df = pd.read_csv(directory_path + '/idirect-stockscriptnew.csv',sep=',',
				encoding='utf-8',header=0,usecols=selectedColumns_idirect_orig)
        indexOnly = df["SG"].str.contains("DERIVATIVE") 
        mask = indexOnly
        df_filtered_idirect_orig = df.loc[mask]
        df_filtered_idirect_orig['TK']=df_filtered_idirect_orig['TK'].astype(int)
        df_filtered_idirect_orig.to_csv(directory_path + '/idirect_orig-filtered.csv', index=False)
        print(df_filtered_idirect_orig.head()) 

        print("Reading unzippped files")
        selectedColumns_zerodha = ['instrument_token','exchange_token','tradingsymbol','segment']
        df = pd.read_csv(directory_path + '/zerodha-instruments.csv',header=0,usecols=selectedColumns_zerodha)
        df = df.rename(columns={'instrument_token':'zerodha_id','segment': 'zsegment','exchange_token':'zexchange_token'})
        indexOnly = df["zsegment"].str.contains("NFO-FUT") | df["zsegment"].str.contains("NFO-OPT")
        mask = indexOnly
        df_filtered_zerodha = df.loc[mask]
        df_filtered_zerodha.to_csv(directory_path + '/zerodha-filtered.csv', index=False)
        print(df_filtered_zerodha.head())

        print("Reading unzippped files")
        selectedColumns_upstox = ['instrument_key','exchange_token','trading_symbol','segment','underlying_type','name']
        df = pd.read_json(directory_path + '/upstox-complete.json')
        df = df[selectedColumns_upstox]
        df = df.rename(columns={'instrument_key':'upstox_id','segment': 'usegment','exchange_token':'uexchange_token','name':'uname'})
        indexOnly = df["usegment"].str.contains("NSE_FO") & df["underlying_type"].str.contains("INDEX")
        mask = indexOnly
        df_filtered_upstox = df.loc[mask]
        df_filtered_upstox.to_csv(directory_path + '/upstox-filtered.csv', index=False)
        print(df_filtered_upstox.head())

        #df_consolidated = pd.concat([df_filtered_idirect,df_filtered_zerodha],axis=1)
        #df_consolidated.to_csv(directory_path + '/instruments-consolidated.csv', index=False)

        #df_i_i = df_filtered_idirect_orig.merge(df_filtered_idirect, how='inner',left_on='TK', right_on='idirect_id')
        df_i_i = df_filtered_idirect
        df_i_z = df_i_i.merge(df_filtered_zerodha, how='inner',left_on='idirect_id', right_on='zexchange_token')
        df_final = df_i_z.merge(df_filtered_upstox, how='inner',left_on='idirect_id', right_on='uexchange_token')
        df_final['ExpiryDate'] = pd.to_datetime(df_final['ExpiryDate'])
        df_final = df_final.sort_values(by=['Series','ShortName','ExpiryDate','StrikePrice'])
        df_final.to_csv(directory_path + '/instruments-final.csv', index=False)
    except Exception as e:
                print("Error occurred while reading unzipped files.")
                print(e)


if __name__ == '__main__':
    clearOldFiles()
    print("Fetching instruments(iDirect)")
    idirectInstruments1 = "https://directlink.icicidirect.com/NewSecurityMaster/SecurityMaster.zip"
    idirectInstruments2 = "https://traderweb.icicidirect.com/Content/File/txtFile/ScripFile/StockScriptNew.csv"
    downloadFile(idirectInstruments1,"./instruments/idirect-securitymaster.zip")
    downloadFile(idirectInstruments2,"./instruments/idirect-stockscriptnew.csv")
    print("Fetching instruments(upstox)")
    upstoxInstruments = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
    downloadFile(upstoxInstruments, "./instruments/upstox-complete.json.gz")
    print("Fetching instruments(zerodha)")
    zerodhaInstruments = "https://api.kite.trade/instruments"
    downloadFile(zerodhaInstruments, "./instruments/zerodha-instruments.csv")

    unzipFiles()
    readFiles()
