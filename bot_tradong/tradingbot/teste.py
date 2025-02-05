import pandas as pd
import ccxt
import numpy as np
import time
from binance.client import Client
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

# Configuração da Conexão
API_KEY = ''
API_SECRET = ''

exchange = ccxt.binance({'apiKey': API_KEY, 'secret': API_SECRET})
client = Client(API_KEY, API_SECRET)

# Definição dos parâmetros
SYMBOL = 'USDT/SHIB'
TIMEFRAME = '1h'  # 1 dia para obter os últimos 300 dias
TRADE_AMOUNT = 500  # Quantidade a negociar
SHORT_WINDOW = 20
LONG_WINDOW = 200
RSI_WINDOW = 14

# Baixar dados da criptomoeda (últimos 300 dias)
def fetch_ohlcv(symbol, timeframe, limit=300):
    print(f"\n📥 Baixando os últimos {limit} dias de dados para {symbol}...")
    data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    print("✅ Dados baixados com sucesso!\n")
    return df

# Calcular indicadores técnicos
def compute_indicators(df):
    print("📊 Calculando indicadores técnicos...")

    # Médias móveis
    df['short_mavg'] = df['close'].rolling(window=SHORT_WINDOW).mean()
    df['long_mavg'] = df['close'].rolling(window=LONG_WINDOW).mean()

    # RSI (Índice de Força Relativa)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=RSI_WINDOW).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_WINDOW).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Bandas de Bollinger
    df['bollinger_high'] = df['close'].rolling(window=SHORT_WINDOW).mean() + (df['close'].rolling(window=SHORT_WINDOW).std() * 2)
    df['bollinger_low'] = df['close'].rolling(window=SHORT_WINDOW).mean() - (df['close'].rolling(window=SHORT_WINDOW).std() * 2)

    df.dropna(inplace=True)
    print("✅ Indicadores calculados com sucesso!\n")
    return df

# Treinar modelo de IA
def train_ai_model(df):
    print("🤖 Treinando IA com base nos indicadores...\n")

    df = df.copy()
    X = df[['short_mavg', 'long_mavg', 'RSI', 'bollinger_high', 'bollinger_low']].values
    y = (df['close'].shift(-1) > df['close']).astype(int).values  # 1 = Sobe, 0 = Cai

    print("🔍 Valores de X (features):")
    print(X[:5])  # Mostra os primeiros 5 valores

    print("\n🔍 Valores de y (rótulos):")
    print(y[:5])  # Mostra os primeiros 5 valores

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    df.loc[:, 'prediction'] = model.predict(scaler.transform(X))
    print("\n✅ Treinamento da IA concluído!\n")
    return df

# Executar ordens com base no sinal da IA
def execute_trade(df):
    print("🚀 Executando estratégia de trading...")

    last_signal = df['prediction'].iloc[-1]
    balance = exchange.fetch_balance()['total']
    price = float(client.get_symbol_ticker(symbol="SHIBUSDT")['price'])

    print(f"\n📊 **Sinal da IA:** {'🟢 COMPRAR' if last_signal == 1 else '🔴 VENDER'}")
    print(f"💰 Saldo Disponível:")
    print(f"USDT: {balance.get('USDT', 0)}")
    print(f"BTC: {balance.get('BTC', 0)}")
    print(f"SHIB: {balance.get('SHIB', 0)}")
    print(f"DOGE: {balance.get('DOGE', 0)}")
    print(f"PEPE: {balance.get('PEPE', 0)}")
    print(f"💲 Preço Atual do {SYMBOL}: {price}")

    # Verifica se a ordem atende ao min_notional da Binance
    min_notional = 10  # Valor mínimo para negociação
    order_value = TRADE_AMOUNT * price

    if last_signal == 1 and balance.get('USDT', 0) >= order_value and order_value >= min_notional:
        place_buy_order(SYMBOL, TRADE_AMOUNT, price)
    elif last_signal == 0 and balance.get('SHIB', 0) >= TRADE_AMOUNT:
        place_sell_order(SYMBOL, TRADE_AMOUNT, price)
    else:
        print("⚠️ Ordem não executada devido a saldo insuficiente ou valor abaixo do min_notional.\n")

# Criar ordem de compra
def place_buy_order(symbol, amount, price):
    try:
        order = exchange.create_limit_buy_order(symbol=symbol, amount=amount, price=price)
        print(f"\n✅ Ordem de COMPRA criada: {order}")
    except Exception as e:
        print(f"❌ Erro ao criar ordem de compra: {e}")

# Criar ordem de venda
def place_sell_order(symbol, amount, price):
    try:
        order = exchange.create_market_sell_order(symbol, amount)
        print(f"\n✅ Ordem de VENDA criada: {order}")
    except Exception as e:
        print(f"❌ Erro ao criar ordem de venda: {e}")

# Execução principal
def main():
    df = fetch_ohlcv(SYMBOL, TIMEFRAME)
    df = compute_indicators(df)
    df = train_ai_model(df)
    execute_trade(df)

if __name__ == "__main__":
    main()

