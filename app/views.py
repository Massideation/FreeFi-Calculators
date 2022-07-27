from django.shortcuts import render
from django.http import JsonResponse,HttpResponse
from app import config
from binance.client import Client
from datetime import datetime as dt
import time
import pytz
import xlwt
import pandas as pd
import pandas_ta as ta
from app.Trading import TradingEnv
import numpy as np

# # for heroku
# csv_dir = "/app/app/data/" 

# for local
csv_dir = "app/data/" 

# creating an instance of the binance api client using API_KEY and API_SECRET
client=Client(config.API_KEY,config.SECRET_KEY)

# dict for all the intervals for data collection
interval_dict ={
    '1DAY':client.KLINE_INTERVAL_1DAY,
    '12HOUR':client.KLINE_INTERVAL_12HOUR,
    '8HOUR':client.KLINE_INTERVAL_8HOUR,
    '6HOUR':client.KLINE_INTERVAL_6HOUR,
    '4HOUR':client.KLINE_INTERVAL_4HOUR,
    '2HOUR':client.KLINE_INTERVAL_2HOUR,
    '1HOUR':client.KLINE_INTERVAL_1HOUR,
    '30MINUTE':client.KLINE_INTERVAL_30MINUTE,
    '15MINUTE':client.KLINE_INTERVAL_15MINUTE,
    '5MINUTE':client.KLINE_INTERVAL_5MINUTE,
    '3MINUTE':client.KLINE_INTERVAL_3MINUTE,
    '1MINUTE':client.KLINE_INTERVAL_1MINUTE,
    '1WEEK':client.KLINE_INTERVAL_1WEEK,
    # '1MONTH':client.KLINE_INTERVAL_1MONTH,
}


intervalsecs = {
    '1DAY': 86400,
    '12HOUR': 43200,
    '8HOUR': 28800,
    '6HOUR': 21600,
    '4HOUR': 14400,
    '2HOUR': 7200,
    '1HOUR': 3600,
    '30MINUTE': 60*30,
    '15MINUTE': 60*15,
    '5MINUTE': 60*5,
    '3MINUTE': 60*3,
    '1MINUTE': 60,
    '1WEEK': 86400*7,
    # '1MONTH': 86400*30,
}

# declaring empty dataframe globaly for storing fetched data
data:pd.DataFrame
# analysis name 
name:str

# utility function to get data from binance
def get_data(symbol,interval,start_date,end_date):

    # Converting UTC to EST time zone ( UTC - 4 hours)
    
    start = start_date #int(dt.strptime(start_date,"%d %B, %Y").timetuple())
    end = end_date #int(dt.strptime(end_date,"%d %B, %Y").timetuple())

    # string representing the coin
    symbol= symbol
    # string representing the interval of interest
    interval = interval
    
    start_timestamp = int(time.mktime(dt.strptime(start,"%Y-%m-%d").timetuple()) - (33 * intervalsecs[interval]))
    end_timestamp = int(time.mktime(dt.strptime(end,"%Y-%m-%d").timetuple()))

    new_start = dt.fromtimestamp(start_timestamp)
    new_start = new_start.strftime("%Y-%m-%d %H:%M:%S") 
    # convert timestamp back to string

    try:
        # getting historical candlestick data from binance
        candles = client.get_historical_klines(symbol=symbol,interval=interval_dict[interval],start_str=new_start,end_str=end)
            # filtering out the required information from the api response
        processed_candlesticks=[]
        for data in candles:
            candlestick={

                "time":int(data[0] * 0.001),
                "open":float(data[1]),
                "high":float(data[2]),
                "low":float(data[3]),
                "close":float(data[4])
            }
            processed_candlesticks.append(candlestick)
        
        candlesticks = pd.DataFrame.from_dict(processed_candlesticks, orient='columns')

        return candlesticks,True

    except NameError:
        print(f"Error Fetching Data: {NameError}")
        return pd.DataFrame([]),False

# utility function to calculate trend
def trend(df):

    max_macdh=-1
    min_macdh=1
    trend=[]
    # if macdh is >0 && curent > previous : dark green sell 5%
    # if macdh is <0 && current < previous : dark red buy 5%
    for i in range(len(df)):
        if df['MACDh'].iloc[i] > 0 and df['MACDh'].iloc[i] > max_macdh:
            min_macdh=1
            trend.append("DARK_GREEN")
            if df['MACDh'].iloc[i] > max_macdh:
                max_macdh=df['MACDh'].iloc[i]

        elif df['MACDh'].iloc[i] > 0 and df['MACDh'].iloc[i] <= max_macdh:
            trend.append("GREEN")

        elif df['MACDh'].iloc[i] < 0 and df['MACDh'].iloc[i] < min_macdh:
            max_macdh=-1
            trend.append("DARK_RED")
            if df['MACDh'].iloc[i] < min_macdh:
                min_macdh=df['MACDh'].iloc[i]

        elif df['MACDh'].iloc[i] < 0 and df['MACDh'].iloc[i] >= min_macdh:
            trend.append("RED")
        else:
            trend.append("")
    
    return trend

# Index view
def index(request):
    
    content = {"result" : False}

    if request.method == 'POST':
        
        global data
        global name

        parameters=request.POST

        # selected coin
        coin = parameters['coin']
        pair = "USDT" #parameters['pair']
        symbol=coin+pair

        # strategy 
        strategy_all_in=False

        start = parameters['start']
        end = parameters['end']

        interval = parameters['interval']
        if parameters['buyPercent'] != "":
            buy_percent = float(parameters['buyPercent'])
        if parameters['sellPercent'] != "":
            sell_percent = float(parameters['sellPercent'])

        # debugging 
        print (f"type : {type(start)} => start : {start} , end: {end}")
        
        start_time=time.mktime(dt.strptime(start,"%Y-%m-%d").timetuple())
        end_time=time.mktime(dt.strptime(end,"%Y-%m-%d").timetuple())

        num_of_candles=((end_time-start_time)+34)/intervalsecs[interval]

        if num_of_candles > 1100: # upto 3 years of analysis on 1 day interval
            
            content['memory_exceeded_limit']=True
            content['interval']=interval
            content['start_date']=start
            content['end_date']=end
            
            return render(request,"index.html",context=content)

        else:
            content['memory_exceeded_limit']=False

            # setting the name of using selected parameters
            name = symbol+'_'+start+'_to_'+end+'_'+interval
            # fetching data from binance and storing in the global data dataframe
            data,status=get_data(symbol,interval,start,end)

            if status:
                # simulate trading
                if parameters['buyPercent'] and parameters['sellPercent'] != "":
                    content= trading_strategy(buy_percentage=buy_percent,sell_percentage=sell_percent,all_in_strategy=strategy_all_in)
                else:
                    content= trading_strategy(all_in_strategy=strategy_all_in)

                # adding variables for displaying 
                content['result']=True
                content['symbol']=coin # symbol => BTCUSDT
                content['interval']=interval
                content['start_date']=start
                content['end_date']=end


    return render(request,"index.html",context=content)

# api endpoint for gettign data for plotting
def fetch_data(request):

    global data

    candles=[]

    signals=[]

    balance=[]

    for i in range(len(data)):
        
        candles.append({'time':int(data['time'].iloc[i]),'open':float(data['open'].iloc[i]),'high':float(data['high'].iloc[i]),'low':float(data['low'].iloc[i]),'close':float(data['close'].iloc[i])})
        
        balance.append({'time': int(data['time'].iloc[i]), 'value': float(data['balance'].iloc[i])})

        if data['buysell'].iloc[i] == "sell" or data['buysell'].iloc[i] == "sell_all":

            signals.append({ 'time': int(data['time'].iloc[i]), 'position': 'aboveBar', 'color': '#e91e63', 'shape': 'arrowDown', 'text': data['buysell'].iloc[i]}) #@ {df['close'].iloc[i] + 2 }

        elif data['buysell'].iloc[i] == "buy" or data['buysell'].iloc[i] == "buy_all":

            signals.append({ 'time': int(data['time'].iloc[i]), 'position': 'belowBar', 'color': '#2196F3', 'shape': 'arrowUp', 'text': data['buysell'].iloc[i]}) # @ {df['open'].iloc[i] - 2 }
    
    # returning json response for the fetch_data api to fetch and render on the graph/plot
    return JsonResponse({'candlesticks':candles,'buysell':signals , 'balance':balance}) #, 'balance':balance
    
# Trading simulation function
def trading_strategy(fast=12,slow=26,signal=9,buy_percentage=5.0,sell_percentage=3.0,all_in_strategy=False):
    
    global data

    result ={}
    
    strategy=all_in_strategy

    data.ta.macd(close="close", fast=fast, slow=slow, signal=signal, append=True)
    # macd column rename
    data.rename(columns  = {f"MACDh_{fast}_{slow}_{signal}" : "MACDh"},inplace=True)
    data['prev_macdh']  = data['MACDh'].shift(1)
    data['trend'] = pd.DataFrame(trend(data))
    data['buysell'] = np.nan
    data['balance'] = np.nan
    data['coin_qty']  = np.nan
    data['coin_balance'] = np.nan

    # VIP level 0, paying fees with BNB = 0.075%
    env = TradingEnv(balance_amount=1000,balance_unit='USDT', trading_fee_multiplier=0.99925,buy_percentage=buy_percentage,sell_percentage=sell_percentage,all_in_strategy=strategy)

    data.loc[0,'balance'] = env.balance_amount
    data.loc[0,'coin_qty'] = env.coin_qty
    
    # simulating trading strategy
    for i in range(len(data)):

        # buy if balance is available
        if env.positive_balance:
            if data['trend'].iloc[i] == "DARK_RED": #buy signal
                env.buy(data['open'].iloc[i], data['time'].iloc[i])
                # df.loc[i,'balance']= env.balance_amount
                data.loc[i,'buysell']= "buy"

            if all_in_strategy:
                if i > 1 and data['trend'].iloc[i] == "RED" and data['trend'].iloc[i-1] == "DARK_RED" and data['trend'].iloc[i-2] == "DARK_RED":
                    env.buy_all(data['open'].iloc[i], data['time'].iloc[i])
                    # df.loc[i,'balance']=env.balance_amount
                    data.loc[i,'buysell']="buy_all"
            
            data.loc[i,'balance'] = env.balance_amount
            data.loc[i,'coin_qty'] = env.coin_qty
        
        # sell if in position, i.e coin is available
        if env.in_position:
            if data['trend'].iloc[i] == "DARK_GREEN": #sell signal
                env.sell(data['close'].iloc[i], data['time'].iloc[i])
                # df.loc[i,'balance'] = env.balance_amount
                data.loc[i,'buysell'] = "sell"
            
            if all_in_strategy:
                if i > 0 and data['trend'].iloc[i] == "GREEN" and data['trend'].iloc[i-1] == "DARK_GREEN" and data['trend'].iloc[i-2] == "DARK_GREEN":
                    env.sell_all(data['close'].iloc[i], data['time'].iloc[i])
                    # df.loc[i,'balance'] = env.balance_amount
                    data.loc[i,'buysell']="sell_all"
 
            data.loc[i,'balance'] = env.balance_amount
            data.loc[i,'coin_qty'] = np.round(env.coin_qty,6)

    # sell all coins at the end if balance is available
    # if env.in_position :
    #     env.sell_all(df['close'].iloc[-1], df['time'].iloc[-1])
    #     df.loc[len(df)-1,'buysell'] = "sell_all"
    
    data.loc[len(data)-1,'balance'] = env.balance_amount
    data.loc[len(data)-1,'coin_qty'] = env.coin_qty
    data['coin_balance']=np.round(data['close']*data['coin_qty'],2)
    data['total_portfolio_value']=data['coin_balance']+data['balance']

    # download_data=df[['time','balance','coin_qty','coin_balance','total_portfolio_value']]

    # print(download_data)

    final_balance =round(data.loc[len(data)-1,'total_portfolio_value'],2)
    final_profit= final_balance-env.starting_balance
    profit_percentage= round(final_profit*100/env.starting_balance,2)

    # calculations for buy and hold
    coin_bought_at_start = env.starting_balance/data['open'].iloc[0]
    balance_after_selling_at_end = coin_bought_at_start*data['close'].iloc[-1]
    bnh_profit=balance_after_selling_at_end - env.starting_balance
    bnh_percentage = (bnh_profit*100) / env.starting_balance

    # saving the analysis to data folder for later use by other apis
    # data.to_csv(file)

    result['final_balance']= round(data.loc[len(data)-1,'total_portfolio_value'],2)
    result['profit'] = round(final_profit,2)
    result['profit_percent'] = round(profit_percentage,2)
    result['buyandhold_balance'] = round(balance_after_selling_at_end,2)
    result['buyandhold_profit'] = round(bnh_profit,2)
    result['bnh_percentage'] = round(bnh_percentage,2)
    result['end_USD'] = round(data.loc[len(data)-1,'balance'],2)
    result['end_Coin'] = round(data.loc[len(data)-1,'coin_balance'],2)
    result['end_portfolio'] = round(data.loc[len(data)-1,'total_portfolio_value'],2)
    result['buy_percent'] = buy_percentage
    result['sell_percent'] = sell_percentage

    return result

# Download excel file
def download_file(request):

    global data
    global name

    # # getting the analysis data from the data folder
    # file=glob.glob(f'{csv_dir}*.csv')[0]
    # setting respose type to be excel
    response = HttpResponse(content_type='application/ms-excel')
    # # setting file name and type as attachment
    # excel_name=file.split(".")[0]
    # excel_name=excel_name[9:]
    response['Content-Disposition'] = f'attachment; filename="{name}.xls" '

    # reading raw data
    raw_data=data
    # creating a new dataframe with only essential data
    download_data=raw_data[['time','trend','buysell','balance','coin_qty','coin_balance','total_portfolio_value']]
    # creating a excel workbook
    wb=xlwt.Workbook()
    # adding sheet to workbook
    ws=wb.add_sheet("Simulation Results")
    # setting font styleherok
    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns=['Time_UTC','Time_EST','MACD_Color','Buy_Or_Sell','USD_balance','Coin_Quantity','Coin_Value_USD','Total_Portfolio_value']
    row_num=0
    for i in range(len(columns)):
        ws.write(row_num,i,columns[i],font_style)

    font_style.font.bold = False
    offset=34
    for i in range(offset,len(download_data)+1):
        # converting timestamp to string format for readability
        utc_time,est_time=UTCtimeStamp_to_EST(download_data['time'].iloc[i-1])

        if download_data['trend'].iloc[i-1] == np.nan:
            trend=""
        else:
            trend=download_data['trend'].iloc[i-1]

        ws.write(i-offset+1, 0, utc_time, font_style)
        ws.write(i-offset+1, 1, est_time, font_style)
        ws.write(i-offset+1, 2, trend, font_style)
        ws.write(i-offset+1, 3, download_data['buysell'].iloc[i-1], font_style)
        ws.write(i-offset+1, 4, download_data['balance'].iloc[i-1], font_style)
        ws.write(i-offset+1, 5, download_data['coin_qty'].iloc[i-1], font_style)
        ws.write(i-offset+1, 6, download_data['coin_balance'].iloc[i-1], font_style)
        ws.write(i-offset+1, 7, download_data['total_portfolio_value'].iloc[i-1], font_style)

    wb.save(response)

    return response

# Converting Timestamp to readable time 
def UTCtimeStamp_to_EST(time):

    est=pytz.timezone('US/Eastern')
    utc=pytz.utc

    fmt='%Y-%m-%d %I:%M:%S %p'

    utc_time = dt.fromtimestamp(int(time))
    est_time = dt.fromtimestamp(int(time - 4*3600))
        
    return utc_time.strftime(fmt),est_time.strftime(fmt)
