# 標的清單設定,每季人工更新一次即可

INDEX_TICKERS = ["SPY", "QQQ", "IWM"]

SECTOR_ETFS = [
    "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLB", "XLU", "XLRE", "XLC",
]

SECTOR_NAMES = {
    "XLK": "科技", "XLF": "金融", "XLE": "能源", "XLV": "醫療保健",
    "XLY": "非必需消費", "XLP": "必需消費", "XLI": "工業", "XLB": "原物料",
    "XLU": "公用事業", "XLRE": "不動產", "XLC": "通訊服務",
}

# 各板塊前10大權值股(yfinance ticker 格式,BRK.B -> BRK-B)
SECTOR_STOCKS = {
    "XLK": ["AAPL", "NVDA", "MSFT", "AVGO", "ORCL", "CRM", "AMD", "ADBE", "CSCO", "ACN"],
    "XLF": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "AXP"],
    "XLE": ["XOM", "CVX", "COP", "EOG", "WMB", "SLB", "OXY", "MPC", "PSX", "VLO"],
    "XLV": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE", "DHR", "ISRG"],
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "BKNG", "TJX", "LOW", "SBUX", "NKE", "CMG"],
    "XLP": ["PG", "COST", "WMT", "KO", "PEP", "PM", "MDLZ", "MO", "CL", "TGT"],
    "XLI": ["GE", "CAT", "RTX", "UBER", "HON", "UNP", "ADP", "BA", "DE", "LMT"],
    "XLB": ["LIN", "SHW", "ECL", "FCX", "APD", "NEM", "DOW", "NUE", "DD", "CTVA"],
    "XLU": ["NEE", "SO", "DUK", "CEG", "AEP", "SRE", "D", "EXC", "XEL", "ED"],
    "XLRE": ["PLD", "AMT", "EQIX", "WELL", "SPG", "PSA", "O", "DLR", "CCI", "VICI"],
    "XLC": ["META", "GOOGL", "GOOG", "NFLX", "DIS", "TMUS", "CMCSA", "VZ", "T", "CHTR"],
}

BTC_TICKER = "BTC-USD"
OKX_FUNDING_URL = "https://www.okx.com/api/v5/public/funding-rate"
OKX_INST_ID = "BTC-USDT-SWAP"
COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"

HISTORY_FILE = "history.json"
DATAPACK_FILE = "datapack.json"

# 個股 logo 用的公司網域(給 Google favicon 服務查圖標,logo.clearbit.com 已經停用/DNS 解不到,改用這個)
# 先補目前有點名到的幾檔,之後換到別的板塊、名單上出現新股票再補進來即可,
# 沒補到的股票 build_roster() 會自動跳過圖標、只顯示文字。
TICKER_DOMAINS = {
    "XOM": "exxonmobil.com",
    "OXY": "oxy.com",
    "COP": "www.conocophillips.com",
    "EOG": "eogresources.com",
    "CVX": "chevron.com",
    "TSLA": "tesla.com",
    "CMG": "chipotle.com",
    "NKE": "nike.com",
    "AMZN": "amazon.com",
    "BKNG": "booking.com",
    "TJX": "tjx.com",
    "SBUX": "starbucks.com",
    "AEP": "aep.com",
    "XEL": "xcelenergy.com",
    "EXC": "exeloncorp.com",
    "CEG": "constellationenergy.com",
    "SRE": "sempra.com",
    "ORCL": "oracle.com",
    "NVDA": "nvidia.com",
    "AVGO": "broadcom.com",
    "MSFT": "microsoft.com",
    "CSCO": "cisco.com",
    "MPC": "marathonpetroleum.com",
    "VLO": "valero.com",
    "ADBE": "adobe.com",
    "PSX": "phillips66.com",
}

# 每週投票用的 Google 表單(嵌入用),題目/選項每週去表單後台改,連結固定不用動
GOOGLE_FORM_EMBED_SRC = "https://docs.google.com/forms/d/e/1FAIpQLSeondxmAqPE6wFsGkRRe1FcNWH3uxbyx60UpR-NYdsEBVALnA/viewform?embedded=true"
