from os import name
from re import template
import alpaca_trade_api as tradeapi
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio

# API Connection
APCA_API_BASE_URL = 'https://paper-api.alpaca.markets'
APCA_API_KEY_ID = 'PKFJQDIO4YXA5YUSAQBS'
APCA_API_SECRET_KEY = 'Y1kiKQp2nwqDx1H4quN7dhHLmTzyeHLHCwGeEZTA'

api = tradeapi.REST(
    base_url=APCA_API_BASE_URL,
    key_id=APCA_API_KEY_ID,
    secret_key=APCA_API_SECRET_KEY,
    api_version='v2'
)

# Asset information
symbol='SPY' # Desired investment asset (Stock, ETF Ticker)
timeframe='15Day' # How ofter you want to invest
start='2021-01-01' 
end='2021-12-01'
limit='1000' # This is set up as 1000 which is the maximum API calls for the free version of Alpaca

# Parameters
dates=[]
close_adj=[]
unrealized_PL=[] # Unrealized profit and loses
shares=[] # Number of shares bought
total_amount_invested=[]
market_value=[]
cost_basis=[]
green_days=0
red_days=0
initial_lump_sum=5000
recurring_investment_amt=100
investment_amt_adjustment=50 # Additional investment to recurring_investment_amt if the market goes down. 0 is no adjustment

# get close price data
asset_all_close = api.get_bars(symbol=symbol,timeframe=timeframe,start=start,end=end,limit=limit,adjustment='all')
close = asset_all_close.df.close

# get dates from close price
for i in range(len(close)):
    txt=[str(asset_all_close[i].t.year),str(asset_all_close[i].t.month),str(asset_all_close[i].t.day)]
    dates.append('-'.join(txt))

# get prices before close_adj
for i in dates:
    NY = 'America/New_York'
    txt_start=[i,'15:00']
    txt_end=[i,'15:30']
    close_adj_start=pd.Timestamp(' '.join(txt_start), tz=NY).isoformat()
    close_adj_end=pd.Timestamp(' '.join(txt_end), tz=NY).isoformat()
    asset_all_close_adj=api.get_barset(symbol,timeframe='minute',start=close_adj_start,end=close_adj_end)
    # calculation of Volume-Weighted Average Price (VWAP)
    close_adj.append(sum(asset_all_close_adj.df[symbol,'close']*asset_all_close_adj.df[symbol,'volume'])/asset_all_close_adj.df[symbol,'volume'].sum())

# Simple Cost-Dollar-Average strategy
for i in range(len(close)):
    if i==0:
        if initial_lump_sum == 0:
            shares.append(recurring_investment_amt/close_adj[i])
            market_value.append(shares[i]*close_adj[i])
            total_amount_invested.append(recurring_investment_amt)
            unrealized_PL.append(market_value[i]-total_amount_invested[i])
        else:
            shares.append(initial_lump_sum/close_adj[i])
            market_value.append(shares[i]*close_adj[i])
            total_amount_invested.append(initial_lump_sum)
            unrealized_PL.append(market_value[i]-total_amount_invested[i])   
    else:
        if close_adj[i] > close_adj[i-1]:
            shares.append(shares[i-1]+recurring_investment_amt/close_adj[i])
            market_value.append(shares[i]*close_adj[i])
            total_amount_invested.append(total_amount_invested[i-1]+recurring_investment_amt)
            unrealized_PL.append(market_value[i]-total_amount_invested[i])
            green_days+=1 # Calculate No. of green days from close_adj to close_adj
        else:
            shares.append(shares[i-1]+(recurring_investment_amt+investment_amt_adjustment)/close_adj[i])
            market_value.append(shares[i]*close_adj[i])
            total_amount_invested.append(total_amount_invested[i-1]+recurring_investment_amt+investment_amt_adjustment)
            unrealized_PL.append(market_value[i]-total_amount_invested[i])
            red_days+=1 # Calculate No. of red days from close_adj to close_adj

# Cost basis calculation
cost_basis = np.linspace(total_amount_invested[len(close)-1]/shares[len(close)-1], total_amount_invested[len(close)-1]/shares[len(close)-1], num=len(close))

# Time-Weighted Rate of Return
amount_invested = []
market_value_return = []
returns = []
TWRR = 1
for i in range(len(close)):
    if i == 0:
        amount_invested.append(0)
        market_value_return.append(market_value[i])   
    else:
        amount_invested.append(total_amount_invested[i]-total_amount_invested[i-1])
        market_value_return.append(market_value[i]-amount_invested[i])
        returns.append(1+((market_value_return[i]-(market_value_return[i-1]+amount_invested[i-1]))/(market_value_return[i-1]+amount_invested[i-1])))
        TWRR = TWRR * returns[i-1]
TWRR = (TWRR - 1) * 100

pio.templates.default = "plotly_white"

# Ploting
fig = make_subplots(rows=4, cols=4,
                    subplot_titles=('Price','','','Shares','','','Market Value','','','Unrealized P&L','',''),
                    shared_xaxes=True,
                    vertical_spacing=0.09,
                    specs=[[{'colspan': 2},None,{'type': 'indicator'},{'type': 'indicator'}],  # first row
                        [{'colspan': 2},None,{'type': 'indicator'},{'type': 'indicator'}],  # second row
                        [{'colspan': 2},None,{'type': 'indicator'},{'type': 'indicator'}],  # third row
                        [{'colspan': 2},None,{'type': 'indicator'},None]]) # Fourth row

fig.add_trace(go.Scatter(x=dates, y=close_adj,name='Price'),row=1, col=1)
fig.add_trace(go.Scatter(x=dates, y=cost_basis,name='Cost Basis'),row=1, col=1)
fig.add_trace(go.Bar(x=dates, y=shares,name='# of Shares'),row=2, col=1)
fig.add_trace(go.Bar(x=dates, y=market_value,name='Market Value'),row=3, col=1)
fig.add_trace(go.Bar(x=dates, y=unrealized_PL,name='Unrealized P&L'),row=4, col=1)

fig.add_trace(go.Indicator(mode = 'number',
                            number={'prefix': '$','font':{'size':60}},
                            value = total_amount_invested[len(close)-1],
                            title = {'text': 'Total Amount Invested','font':{'size':20}}),
                            row=1, col=3)

fig.add_trace(go.Indicator(mode = 'number',
                            number={'font':{'size':60}},
                            value = shares[len(close)-1],
                            title = {'text': 'Current # of Shares','font':{'size':20}}),
                            row=2, col=3)

fig.add_trace(go.Indicator(mode = 'number',
                            number={'prefix': '$','font':{'size':60}},
                            value = market_value[len(close)-1],
                            title = {'text': 'Current Market Value','font':{'size':20}}),
                            row=3, col=3)

fig.add_trace(go.Indicator(mode = 'number',
                            number={'prefix': '$','font':{'size':60}},
                            value = unrealized_PL[len(close)-1],
                            title = {'text': 'Current Unrealized P&L','font':{'size':20}}),
                            row=4, col=3)

fig.add_trace(go.Indicator(mode = 'number',
                            number={'prefix': '%','font':{'size':60}},
                            value = TWRR,
                            title = {'text': 'Time-Weighted Rate of Return','font':{'size':20}}),
                            row=1, col=4)

fig.add_trace(go.Indicator(mode = 'delta',
                            value = 2*green_days,
                            delta = {'reference': green_days},
                            number={'font':{'size':60}},
                            title = {'text': '# Green Days','font':{'size':20}}),
                            row=2, col=4)

fig.add_trace(go.Indicator(mode = 'delta',
                            value = 0,
                            delta = {'reference': red_days},
                            number={'font':{'size':60}},
                            title = {'text': '# Red Days','font':{'size':20}}),
                            row=3, col=4)

txt = ['Dollar-Cost-Average Strategy - ',symbol]
fig.update_layout(width=1700, title_text=' '.join(txt))
fig.show()


