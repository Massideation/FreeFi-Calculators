from django.shortcuts import render
from django.http import JsonResponse,HttpResponse
from app import config
from binance.client import Client
from datetime import datetime as dt
import glob
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
            
            # setting the name of using selected parameters
            name = coin+'_'+start+'_to_'+end+'_'+interval+'_'+str(content['buy_percent'])+'_'+str(content['sell_percent'])

    return render(request,"index.html",context=content)

# view for wealth building table page
def wealth_building(request):

    content={
            'result' :False,
            'years' : [1,2,3,4,5,6,7,8,9,10],
            'income' : [0,0,0,0,0,0,0,0,0,0],
            'exoense' :[0,0,0,0,0,0,0,0,0,0],
            'asset': [0,0,0,0,0,0,0,0,0,0],
            'usdc': [0,0,0,0,0,0,0,0,0,0],
            'usdc_interest' : [0,0,0,0,0,0,0,0,0,0],
            'asset_growth' : [0,0,0,0,0,0,0,0,0,0],
            'total_colleteral' : [0,0,0,0,0,0,0,0,0,0],
            'loan_interest': [0,0,0,0,0,0,0,0,0,0],
            'net_colleteral' : [0,0,0,0,0,0,0,0,0,0],
            'invest_whats_left' : [0,0,0,0,0,0,0,0,0,0],
            'FFM' : [0,0,0,0,0,0,0,0,0,0],
            'inv_diff_months' : [0,0,0,0,0,0,0,0,0,0],
        }

    if request.method == 'POST':

        input = request.POST
        income = float(input['income'].replace(",",""))*12
        expense=float(input['expense'].replace(",",""))*12
        asset_percent= float(input['asset_percent'])
        num_yrs = int(float(input['numyears'].replace(",",".")))
        usdc_interest= float(input['USDC_interest'].replace(",","."))
        loan_interest= float(input['Loan_interest'].replace(",","."))
        asset_gain= float(input['Asset_gain'].replace(",","."))

        asset = income*asset_percent/100
        
        cash = income*(100-asset_percent)/100
        
        cash_plus_interest = cash + (cash * usdc_interest/100)
        
        asset_plus_growth = asset + (asset * asset_gain/100)

        loan_plus_interest = expense + (expense * loan_interest/100)

        total_collateral = cash_plus_interest + asset_plus_growth

        net_collatteral = total_collateral - loan_plus_interest

        invest_whats_left = income-expense

        FFM = np.round(net_collatteral*12/expense,2)

        inv_diff_months= np.round(invest_whats_left*12/expense,2)

        years =[1,]
        income_list = [income]
        expense_list = [expense]
        assets_list = [asset,]
        cash_list = [cash,]
        cash_plus_interest_list = [cash_plus_interest,]
        asset_growth_list =[asset_plus_growth,]
        collateral_list = [total_collateral,]
        loan_interest_list=[loan_plus_interest,]
        net_collateral_list = [net_collatteral,]
        invest_whats_left_list = [invest_whats_left,]
        FFM_list = [FFM,]
        inv_diff_months_list= [inv_diff_months,]



        for i in range(1,num_yrs):
          
            years.append(i+1)

            income_list.append(income*(i+1))

            expense_list.append(expense*(i+1))

            asset = income*asset_percent/100

            assets_list.append(asset)

            cash = cash_list[i-1] + income*(100-asset_percent)/100
            cash_list.append(cash)

            cash_plus_interest = (cash_plus_interest_list[i-1] + asset) * (1+(usdc_interest/100))
            cash_plus_interest_list.append(cash_plus_interest)

            asset_plus_growth = (asset_growth_list[i-1] +  asset) * (1+(asset_gain/100))
            asset_growth_list.append(asset_plus_growth)

            loan_plus_interest = (loan_interest_list[i-1] + expense)*(1+(loan_interest/100))
            loan_interest_list.append(loan_plus_interest)

            total_collateral = cash_plus_interest + asset_plus_growth
            collateral_list.append(total_collateral)

            net_collateral = total_collateral - loan_plus_interest
            net_collateral_list.append(net_collateral)

            invest_whats_left = (invest_whats_left_list[i-1] + (income-expense))*(1+(asset_gain/100))
            invest_whats_left_list.append(invest_whats_left)

            FFM = net_collateral_list[i]*12/expense
            FFM_list.append(np.round(FFM,2))

            inv_diff_months= invest_whats_left_list[i]*12/expense
            inv_diff_months_list.append(np.round(inv_diff_months,2))

        parameter_list = ['Monthly Income','Monthly Expenses','Asset Allocation %','Investment Years','USDC Interest %','Loan Interest %','Asset Gain %(CAGR)']
        selected_list = [income/12,expense/12,asset_percent,num_yrs,usdc_interest,loan_interest,asset_gain]
        
        content={
            'result' :True,
            'years' : years,
            'income' : income_list,
            'expense' : expense_list,
            'asset': assets_list,
            'usdc': cash_list,
            'usdc_interest' : cash_plus_interest_list,
            'asset_growth' : asset_growth_list,
            'total_colleteral' : collateral_list,
            'loan_interest': loan_interest_list,
            'net_colleteral' : net_collateral_list,
            'invest_whats_left' : invest_whats_left_list,
            'FFM' : FFM_list,
            'inv_diff_months' : inv_diff_months_list,
            'parameters' : parameter_list,
            'selected_params' : selected_list,
        }
        
    return render(request,"wealth_building.html",context=content)

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
                data.loc[i,'buysell']= "buy"

            if all_in_strategy:
                if i > 1 and data['trend'].iloc[i] == "RED" and data['trend'].iloc[i-1] == "DARK_RED" and data['trend'].iloc[i-2] == "DARK_RED":
                    env.buy_all(data['open'].iloc[i], data['time'].iloc[i])
                    data.loc[i,'buysell']="buy_all"
            
            data.loc[i,'balance'] = env.balance_amount
            data.loc[i,'coin_qty'] = env.coin_qty
        
        # sell if in position, i.e coin is available
        if env.in_position:
            if data['trend'].iloc[i] == "DARK_GREEN": #sell signal
                env.sell(data['close'].iloc[i], data['time'].iloc[i])
                data.loc[i,'buysell'] = "sell"
            
            if all_in_strategy:
                if i > 0 and data['trend'].iloc[i] == "GREEN" and data['trend'].iloc[i-1] == "DARK_GREEN" and data['trend'].iloc[i-2] == "DARK_GREEN":
                    env.sell_all(data['close'].iloc[i], data['time'].iloc[i])
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

    # estimating performance metrics
    final_balance =round(data.loc[len(data)-1,'total_portfolio_value'],2)
    final_profit= final_balance-env.starting_balance
    profit_percentage= round(final_profit*100/env.starting_balance,2)

    # calculations for buy and hold
    coin_bought_at_start = env.starting_balance/data['open'].iloc[0]
    balance_after_selling_at_end = coin_bought_at_start*data['close'].iloc[-1]
    bnh_profit=balance_after_selling_at_end - env.starting_balance
    bnh_percentage = (bnh_profit*100) / env.starting_balance

    # data returned from this function
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

# api end point for Downloading excel file
def download_file(request):

    global data
    global name

    print(name)
    # setting respose type to be excel
    response = HttpResponse(content_type='application/ms-excel')
    # setting file name and type as attachment
    response['Content-Disposition'] = f'attachment; filename="{name}.xls" '
    # reading raw data
    raw_data=data
    # creating a new dataframe with only essential data
    download_data=raw_data[['time','trend','buysell','balance','coin_qty','coin_balance','total_portfolio_value']]
    # creating a excel workbook
    wb=xlwt.Workbook()
    # adding sheets to workbook
    ws=wb.add_sheet("Simulation Results")
    ws1=wb.add_sheet("Selected Parameters")

    # adding transaction data to worksheet
    # setting font styleherok
    font_style_header = xlwt.XFStyle()
    font_style_header.font.bold = True

    columns=['Time_UTC','Time_EST/EDT','MACD_Color','Transaction_USD','Balance_USD','Coin_Quantity','Coin_Value_USD','Total_Portfolio_value']
    row_num=0
    for i in range(len(columns)):
        ws.write(row_num,i,columns[i],font_style_header)

    font_style_rows = xlwt.XFStyle()
    font_style_rows.font.bold = False

    offset=34
    for i in range(offset,len(download_data)+1):
        # converting timestamp to string format for readability
        utc_time,est_time=UTCtimeStamp_to_EST(download_data['time'].iloc[i-1])

        if download_data['trend'].iloc[i-1] == np.nan:
            trend=""
        else:
            trend=download_data['trend'].iloc[i-1]

        transaction=np.round(download_data['balance'].iloc[i-1]-download_data['balance'].iloc[i-2],2)
        if transaction < 0.0:
            transaction_value = "USD "+str(-transaction)+" BUY"
        elif transaction > 0.0:
            transaction_value = "USD "+str(transaction)+" SELL"
        else:
            transaction_value = "No Transaction"

        ws.write(i-offset+1, 0, utc_time, font_style_rows)
        ws.write(i-offset+1, 1, est_time, font_style_rows)
        ws.write(i-offset+1, 2, trend, font_style_rows)
        ws.write(i-offset+1, 3, transaction_value,font_style_rows)
        ws.write(i-offset+1, 4, np.round(download_data['balance'].iloc[i-1],2), font_style_rows)
        ws.write(i-offset+1, 5, np.round(download_data['coin_qty'].iloc[i-1],2), font_style_rows)
        ws.write(i-offset+1, 6, np.round(download_data['coin_balance'].iloc[i-1],2), font_style_rows)
        ws.write(i-offset+1, 7, np.round(download_data['total_portfolio_value'].iloc[i-1],2), font_style_rows)

    # adding parameter data to second worksheet
    columns_ws1=['Parameter','Value']
    row_num=0
    for i in range(len(columns_ws1)):
        ws1.write(row_num,i,columns_ws1[i],font_style_header)

    values=name.split("_")
    params=['Coin','Start Date',' ','End Date','Interval','Buy %','Sell %']

    for i in range(len(values)-1):
        if i<2:
            ws1.write(i+1,0,params[i],font_style_header)
            ws1.write(i+1,1,values[i],font_style_rows)
        else:
            ws1.write(i+1,0,params[i+1],font_style_header)
            ws1.write(i+1,1,values[i+1],font_style_rows)

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
