from sovtoken.transactions import TokenTransactions

INPUTS = 'inputs'
OUTPUTS = 'outputs'
EXTRA = 'extra'
ADDRESS = 'address'
SIGS = 'signatures'
RESULT = 'result'
AMOUNT = 'amount'
SEQNO = 'seqNo'
PAYMENT_ADDRESS = "paymentAddress"

TOKEN_LEDGER_ID = 1001

MINT_PUBLIC = TokenTransactions.MINT_PUBLIC.value
XFER_PUBLIC = TokenTransactions.XFER_PUBLIC.value
GET_UTXO = TokenTransactions.GET_UTXO.value

ACCEPTABLE_TXN_TYPES = (MINT_PUBLIC, XFER_PUBLIC, GET_UTXO)

UTXO_CACHE_LABEL = "utxo_cache"

ACCEPTABLE_WRITE_TYPES = {TokenTransactions.MINT_PUBLIC.value,
                          TokenTransactions.XFER_PUBLIC.value}
ACCEPTABLE_QUERY_TYPES = {TokenTransactions.GET_UTXO.value, }
ACCEPTABLE_ACTION_TYPES = {}

UTXO_LIMIT = 1000
NEXT_SEQNO = "next"
FROM_SEQNO = "from"
