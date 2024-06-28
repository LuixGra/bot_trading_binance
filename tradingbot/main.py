#importando dependencias

import pandas as pd
import ccxt
import numpy as np
import time


#"criando" sua conta
apiKey = 'YOUR_API_KEY'
api_secret = 'YOUR_SECRET'

exchange = ccxt.binance({
    'apiKey': apiKey,
    'secret': api_secret
})

client = apiKey, api_secret

#func fetch data: dataframa pandas que contem as informações que você requisitar(dependendo dotipo)
#num certo periodo de tempo (timeframe)
#try except

def fetch_ohlcv(symbol, timeframe, since=None, limit=100):
    print("Fetching data")
    for i in range(0,5):
        try:
            print(f"Fetching data for {symbol} with timeframe {timeframe}...")
            data = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            

            print("Data fetched successfully")
            return df
        except ccxt.NetworkError as e:
            print(f"Network error: {e}. Retrying...")
            time.sleep(5)
        except Exception as e:
            print(f"An error occured: {e}")
            break


        return None


##func calcula o famoso BOILLINGBANDS, que seria a diferença de bandas do grafico
#seria basicamente a diferença do movimento da ação pelo gráfico //Fortissimo indicativo
def boilingBands(df, short_window):
    sma = df['short_mavg']
    std = df['close'].rolling(window=short_window).std()
    upper_band = sma + (std * 2)
    lower_band = sma - (std * 2)
    return upper_band, lower_band

#calculando medias móveis do dataframe, numa janela, no caso, dias
#as medias móveis são um indicador levemente importante na hora de calcular uma
#decisão

def calculate_moving_averages(df, short_window, long_window):
    
    try:
        print("Calculating moving averages...")
        df['short_mavg'] = df['close'].rolling(window=short_window).mean()
        df['long_mavg'] = df['close'].rolling(window=long_window).mean()

    except KeyError as e:
        print(f"KeyError: '{e}'")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return df


#pegando a ação (market) da api com o symbol provido
def get_symbol_info(symbol):
    markets = exchange.load_markets()
    return markets[symbol]


#funçao que gera sinais de compra ou venda
#criando o indicador RSI, que é um forte indicador na hora de decidir
#compra
def generate_signals(df, short_window=14, buy_threshold=30, sell_threshold=70):
    #calcular RSI
    delta = df['close'].diff()
    gain = (delta.where(delta> 0,0)).rolling(window=short_window).mean()
    loss = (-delta.where(delta< 0,0)).rolling(window=short_window).mean()
    RS = gain/loss
    RSI = 100 - (100/(1+RS))


    #finalmente gera o sinal
    df['signal'] = 0
    df.loc[df['close'] > df['close'].shift(1), 'signal'] = 1 #sinal de compra se o preço for maior q o anterior
    df.loc[RSI < buy_threshold, 'signal'] = 1 #sinal de compra se RSI estiver abaixo do preço de cOMPRA

    #loop para "enxergar" as diferenças de banda no gráfico
    for i in range(1, len(df)):
        if df['close'].iloc[i] < df['lower_band'].iloc[i] and df['close'].iloc[i-1] > df['lower_band'].iloc[i-1]:
            df['signal'].iloc[i] = 1
        elif df['close'].iloc[i] > df['upper_band'].iloc[i] and df['close'].iloc[i-1] < df['upper_band'].iloc[i-1]:
            df['signal'].iloc[i] = -1
    

    df.loc[(df['close'] < df['close'].shift(1)) & (RSI > sell_threshold), 'signal'] = -1

    # calcular posicao com base no sinal
    df['position'] = df['signal'].diff()

    return df

#func estrategia, aplicando a estrategia desenvolvida no codigo
def strategy(df, symbol, trade_amount, price):
    last_signal = df['position'].iloc[-1]

    #verificar saldo na binance
    saldo = exchange.fetch_balance()
    try:   
        trade_amount = ajustarMin(symbol, trade_amount)
        
    except Exception as e:
        print(f"Erro ao arredondar trade amount: {e}")

        

    #verifica saldo    
    if 'USDT' in saldo and saldo ['USDT']['free'] > 0:
        if last_signal == 1:
            print("Executando ordem de compra!")
            place_buy_order(symbol, trade_amount, price)#compra
        elif last_signal == -1:
            print("Executando ordem de venda")
            sell_order(symbol, trade_amount)#venda
        else:
            print("Nenhum sinal de ordem emitido/detectado")
    else:
        print(f"Saldo insuficiente.")

    
#funçao qe compra ação //API
def place_buy_order(symbol, amount, price):
    try:
        order = exchange.create_market_buy_order(symbol, amount)
        print(f"Ordem de compra criada: {order}")
    except ccxt.ExchangeError as e:
        print(f"Erro ao criar ordem de compra: {e}")
    except Exception as e:
        print(f"Error occured while buying: {e}")
    


#funcao que vende açao //API    
def sell_order(symbol, amount):
    try:
        order = exchange.create_market_sell_order(symbol, amount)
        print(f"Sell order: {order}")
    except Exception as e:
        print(f"Error occured: {e}")


#func tentativa de ajustar o minimo tradavel no mercado
def ajustarMin(symbol, trade_amount):
    symbol_info = get_symbol_info(symbol)
    
    min_notional = None
    for f in symbol_info['info']['filters']:
        if f['filterType'] == 'MIN_NOTIONAL':
            min_notional = float(f['minNotional'])
            break

    if min_notional is None:
        raise ValueError("Min notional filter not found for the symbol")
    
    ticker = exchange.fetch_ticker(symbol)
    current_price = ticker['last']
    
    notional_value = trade_amount * current_price
    if notional_value < min_notional:
        adjusted_amount = min_notional / current_price
        print(f"Trade amount adjusted from {trade_amount} to {adjusted_amount} to meet minimum notional value.")
        return adjusted_amount
    return trade_amount


#configurações
symbol = 'DOGE/USDT'
timeframe = '1h'
short_window = 20
long_window = 200
trade_amount = 8.8  # Quantidade a ser negociada
running = True
buy_threshold = 30
price = 0.20
sell_threshold = 70



#loop principal
while running:
    
    #data
    df = fetch_ohlcv(symbol, timeframe)
    if df is not None:
        print("Data fetched successufully")
        print(df.tail())
        df = calculate_moving_averages(df, short_window, long_window)
        print("Moving averages calculated")
        
        df['upper_band'], df['lower_band'] = boilingBands(df,short_window)
        df = generate_signals(df, short_window, buy_threshold, sell_threshold)
        print("Signals generated!")
        print(df.tail())

        strategy(df, symbol, trade_amount, price)

        




    else:
        print("Error while fetching data")

    info = get_symbol_info(symbol)

    

    print("Script finalizado.\nReiniciando...")
    time.sleep(20)
    print("Em 3...")
    time.sleep(2)
    print("...2...")
    time.sleep(2)
    print("...1...")
    time.sleep(2)



