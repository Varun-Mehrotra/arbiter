# Arbiter

This project is a command line tool for conducting [Trianglular Arbitrage](https://www.investopedia.com/terms/t/triangulararbitrage.asp) trading across a Crypto exchange.

# Usage
Current supported exchanges are `crypto.com` and `coinbasepro`

## Installing the Arbiter
To install the arbiter, ensure that you have an up-to-date version of setuptools installed,

```
python -m pip install --upgrade setuptools
```
and then run

```
python setup.py install
```

## Creating a Session
To create a session, select a supported exchange. To view all exchanges you can run

```
arbiter --help
```

Then supply the required arguments, which can also be listed by a `--help` option on the exchange as such:

```
arbiter <exchange-reference> --help
```
