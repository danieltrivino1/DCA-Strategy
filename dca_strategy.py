from os import name
from re import template
import alpaca_trade_api as tradeapi
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio

# Connect API
APCA_API_BASE_URL = 'https://paper-api.alpaca.markets'
APCA_API_KEY_ID = 'PKFFJ9KONT9YOE87A4MC'
APCA_API_SECRET_KEY = 'oZbpMb6QoRmO2ZIY7uCo9UovzQB7hqa5bpLKLPSa'

api = tradeapi.REST(
    base_url=APCA_API_BASE_URL,
    key_id=APCA_API_KEY_ID,
    secret_key=APCA_API_SECRET_KEY,
    api_version='v2'
)

# Asset information
symbol='SPY'
timeframe='1Day'
start='2021-01-01'
end='2021-06-01'
limit='1000'

# Parameters
dates=[]
close=[]
unrealized_PL=[]
shares=[]
amount_invested=[]
market_value=[]
cost_basis=[]
green_days=0
red_days=0
initial_lump_sum=0
recurring_investment_amt=100
investment_amt_adjustment=0

# get open price data 
asset_all_open = api.get_bars(symbol=symbol,timeframe=timeframe,start=start,end=end,limit=limit,adjustment='all')
open = asset_all_open.df.open

# get dates from open price
for i in range(len(open)):
    txt=[str(asset_all_open[i].t.year),str(asset_all_open[i].t.month),str(asset_all_open[i].t.day)]
    dates.append('-'.join(txt))

# get prices before close
for i in dates:
    NY = 'America/New_York'
    txt_start=[i,'15:00']
    txt_end=[i,'15:03']
    close_start=pd.Timestamp(' '.join(txt_start), tz=NY).isoformat()
    close_end=pd.Timestamp(' '.join(txt_end), tz=NY).isoformat()
    asset_all_close=api.get_barset(symbol,timeframe='minute',start=close_start,end=close_end)
    # calculation of Volume-Weighted Average Price (VWAP)
    close.append(sum(asset_all_close.df[symbol,'close']*asset_all_close.df[symbol,'volume'])/asset_all_close.df[symbol,'volume'].sum())

# Simple Cost-Dollar-Average strategy
for i in range(len(open)):
    if i==0:
        if initial_lump_sum == 0:
            shares.append(recurring_investment_amt/close[i])
            market_value.append(shares[i]*close[i])
            amount_invested.append(recurring_investment_amt)
            unrealized_PL.append(market_value[i]-amount_invested[i])
        else:
            shares.append(initial_lump_sum/close[i])
            market_value.append(shares[i]*close[i])
            amount_invested.append(initial_lump_sum)
            unrealized_PL.append(market_value[i]-amount_invested[i])   
    else:
        if close[i] > close[i-1]:
            shares.append(shares[i-1]+recurring_investment_amt/close[i])
            market_value.append(shares[i]*close[i])
            amount_invested.append(amount_invested[i-1]+recurring_investment_amt)
            unrealized_PL.append(market_value[i]-amount_invested[i])
            green_days+=1 # Calculate No. of green days from close to close
        else:
            shares.append(shares[i-1]+(recurring_investment_amt+investment_amt_adjustment)/close[i])
            market_value.append(shares[i]*close[i])
            amount_invested.append(amount_invested[i-1]+recurring_investment_amt+investment_amt_adjustment)
            unrealized_PL.append(market_value[i]-amount_invested[i])
            red_days+=1 # Calculate No. of red days from close to close

cost_basis=np.linspace(amount_invested[len(open)-1]/shares[len(open)-1], amount_invested[len(open)-1]/shares[len(open)-1], num=len(open))

pio.templates.default = "plotly_white"

# Ploting
fig = make_subplots(rows=4, cols=4,
                    subplot_titles=('Price','','','Shares','','','Market Value','','Unrealized P&L','',''),
                    shared_xaxes=True,
                    vertical_spacing=0.06,
                    specs=[[{'colspan': 2},None,{'type': 'indicator'},{'type': 'indicator'}],  # first row
                        [{'colspan': 2},None,{'type': 'indicator'},{'type': 'indicator'}],  # second row
                        [{'colspan': 2},None,{'type': 'indicator'},None],  # third row
                        [{'colspan': 2},None,{'type': 'indicator'},None]]) # Fourth row

fig.add_trace(go.Scatter(x=dates, y=close,name='Price'),row=1, col=1)
fig.add_trace(go.Scatter(x=dates, y=cost_basis,name='Cost Basis'),row=1, col=1)
fig.add_trace(go.Bar(x=dates, y=shares,name='# of Shares'),row=2, col=1)
fig.add_trace(go.Bar(x=dates, y=market_value,name='Market Value'),row=3, col=1)
fig.add_trace(go.Bar(x=dates, y=unrealized_PL,name='Unrealized P&L'),row=4, col=1)

fig.add_trace(go.Indicator(mode = 'number',
                            number={'prefix': '$','font':{'size':60}},
                            value = amount_invested[len(open)-1],
                            title = {'text': 'Total Amount Invested','font':{'size':20}}),
                            row=1, col=3)

fig.add_trace(go.Indicator(mode = 'number',
                            number={'font':{'size':60}},
                            value = shares[len(open)-1],
                            title = {'text': 'Current # of Shares','font':{'size':20}}),
                            row=2, col=3)

fig.add_trace(go.Indicator(mode = 'number',
                            number={'prefix': '$','font':{'size':60}},
                            value = market_value[len(open)-1],
                            title = {'text': 'Current Market Value','font':{'size':20}}),
                            row=3, col=3)

fig.add_trace(go.Indicator(mode = 'number',
                            number={'prefix': '$','font':{'size':60}},
                            value = unrealized_PL[len(open)-1],
                            title = {'text': 'Current Unrealized P&L','font':{'size':20}}),
                            row=4, col=3)

fig.add_trace(go.Indicator(mode = 'delta',
                            value = 2*green_days,
                            delta = {'reference': green_days},
                            number={'font':{'size':60}},
                            title = {'text': '# Green Days','font':{'size':20}}),
                            row=1, col=4)

fig.add_trace(go.Indicator(mode = 'delta',
                            value = 0,
                            delta = {'reference': red_days},
                            number={'font':{'size':60}},
                            title = {'text': '# Red Days','font':{'size':20}}),
                            row=2, col=4)

txt = ['Dollar-Cost-Average Strategy - ',symbol]
fig.update_layout(width=1700, title_text=' '.join(txt))
fig.show()


