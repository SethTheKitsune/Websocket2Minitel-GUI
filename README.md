# Websocket2Minitel-GUI
A GUI (tkinter) version of Websocket2Minitel, originally made by cquest (https://github.com/cquest/websocket2minitel)

!! This is not Enterprise software, it's the result of an all-nighter. DON'T EXPECT STABILITY. YOU WILL BE DISAPPOINTED IF YOU DO. !!

##Added Features:

###- Speed Dial:

The program now presents a Speed Dial list on the left side, where you can save your WebSocket URLs
by typing them in the appropriate field and clicking "Add", as well as remove them
by selecting the URL from the list and clicking "Remove". The program will automatically create a favorites.json
file where all the saved URLs will be stored.

###- Log box:

I also added a log box on the bottom-right of the window. It's pretty much self-explainatory though.

##- Additional notes:

Because of Windows being Windows and keeping the ports busy for quite a while, even after disconnecting, you will need to
restart the program if you wanna reconnect immediately after disconnecting without waiting (to change the URL for example). I found
no way of getting around it yet. Sorry :/
