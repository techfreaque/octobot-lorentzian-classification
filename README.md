

# octobot-lorentzian-classification
OctoBot Lorentzian Classification evaluator, based on the trading view indicator from ©jdehorty https://www.tradingview.com/script/WhBzgfDu-Machine-Learning-Lorentzian-Classification/

# Still work in progress!
## To Do
* RMA is slightly different as on trading view (probably not a rounding issue)
* gaussian method returns slightly different as on tradingview (probably rounding issue)
* classify_current_candle / prediction is different (probably my implementation is not replicating the original code OR because of differences of available candle data lengths)


# installation
1. Make sure you have the latest OctoBot version ready -> https://octobot.online
2. to be able to install Tentacles, enable a login password for your OctoBot under "Accounts -> Interface"
3. then go to yourOctobotDomain.com:5001/advanced/tentacle_packages - paste the URL for the latest version (see at the bottom) and install it


# Tentacle Package Download URL
https://raw.githubusercontent.com/techfreaque/octobot-lorentzian-classification/main/releases/latest/any_platform.zip

# Octobot Charting Support
* To be able to display plots from this trading mode you can install octo-ui2 from here: https://github.com/techfreaque/octo-ui-2
