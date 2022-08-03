import click
import ccxt

from arbiter.arbiter import Arbiter

@click.group()
def cli():
    pass

@click.command()
@click.argument('apikey')
@click.argument('secret')
@click.option('--base', default='USDT', help='Base currency to arbitrage against')
@click.option('--fee', default=0.4, help='Trading fee per transaction')
@click.option('--profit', default=4, help='Minimum Profit to execute trades on')
def cryptocom(apikey, secret, base, fee, profit):
    """crypto.com triangular arbitrage execution"""

    public = ccxt.cryptocom({
        'rateLimit': 50,
        'enableRateLimit': True
    })

    private = ccxt.cryptocom({
        'apiKey': apikey,
        'secret': secret,
        'rateLimit': 100,
        'enableRateLimit': True,
    })

    # Verify that the credentials are valid for the private exchange object
    private.check_required_credentials()

    arbiter = Arbiter(public, private)

    arbiter.triangular_listener(base, fee/100, profit/100)

@click.command()
@click.argument('apikey')
@click.argument('secret')
@click.argument('password')
@click.option('--base', default='USDT', help='Base currency to arbitrage against')
@click.option('--fee', default=0.6, help='Trading fee per transaction')
@click.option('--profit', default=4, help='Minimum Profit to execute trades on')
def coinbasepro(apikey, secret, password, base, fee, profit):
    """coinbasepro triangular arbitrage execution"""

    public = ccxt.coinbasepro({
        'rateLimit': 50,
        'enableRateLimit': True
    })

    private = ccxt.coinbasepro({
        'apiKey': apikey,
        'secret': secret,
        'password': secret,
        'rateLimit': 100,
        'enableRateLimit': True,
    })

    # Verify that the credentials are valid for the private exchange object
    private.check_required_credentials()

    arbiter = Arbiter(public, private)

    arbiter.triangular_listener(base, fee/100, profit/100)


cli.add_command(coinbasepro)
cli.add_command(cryptocom)
