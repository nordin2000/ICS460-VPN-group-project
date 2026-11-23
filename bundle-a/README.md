This project uses Docker to create a test lab with one museum-server and three remote sites (site-north, site-east, and site-west). The museum-server (nginx) is a web server that shows our web page museum-net (address 172.28.0.10). The museum-server and the three remote sites are on different networks, so the sites can't reach the server yet. Connecting them is what the VPN is for.

# Install Docker
If Docker is not installed, install Docker at https://www.docker.com/products/docker-desktop/

Notes for Windows: 
Download the Docker installer.exe file for windows.
On the Configuration screen, make sure "WSL 2" is selected for the Recommended Per-user installation to support Linux. Restart your computer after the install if prompted. 
You do not need a Docker account for this project so you can skip logging in.
Wait until Docker Desktop says it's running (the whale icon in the taskbar stops moving).

Run the command in PowerShell:

   wsl --install

To run PowerShell in Windows: 

   Start button, or the Windows key. Type PowerShell. Right-click and choose "Run as administrator".

Then, restart your computer, and open Docker Desktop again. 
Keep in mind that WSL 2 is a Windows feature that lets Windows run Linux on your machine. Docker needs it because our containers run Linux. So if you get prompted to set a username and password, remember this in case you use WSL for a future project that uses Linux.

Notes for Apple Mac:
Download the Processor version.
Open the downloaded Docker.dmg file and drag the Docker icon into the Applications folder.
Open Docker from your Applications folder. 
You do not need a Docker account for this project so you can skip logging in.
Wait until the whale icon in the top menu bar stops moving. Docker is now running.

# Confirm Docker works
Open PowerShell (Start button, or the Windows key. Type PowerShell. Right-click and choose "Run as administrator".)

Run the commands:

   docker --version
   docker run hello-world

The first command shows which version of Docker is installed. 
The second command downloads a tiny test container and runs it. You should see a message that starts with "Hello from Docker!" If you do, Docker is installed correctly.
Remember: Docker Desktop must be open whenever you use the lab.

# Open a terminal in the project folder to start the lab
Once you get the files from GitHub, locate the folder you saved them in.
Change to that directory using the cd command. 

Run the command:

   cd /mnt/c/Users/<YourUsername>/Downloads/bundle-a

You can check to make sure you're in the right place by listing the files.

Run the command:

   ls

You should see README.md, docker-compose.yml, index.html files.

Run the command:

   docker compose up -d

Docker looks for and reads the docker-compose.yml file to figure out that it need to download the nginx server and alpine image
(only the first time), create the two networks, and start the four containers. the "-d" runs the command in the background so you get your terminal back.

Run the command:

   docker ps

This command should show 4 containers (museum-server, site-north, site-east, site-west) with a statuses of "Up".

Run the command:

   docker exec museum-server wget -qO- http://localhost

This command will test that the museum server can load the web page. You should see the INDEX.html.

Run the command:

   docker exec site-north wget -T 3 -qO- http://172.28.0.10

This command should test a remote site with no VPN set up yet. "-T 3" means give up after 3 seconds.
The site is on a different network, and there is no VPN yet. Once the VPN is set up, this same command should show the web page. 

Run the command:

   docker compose down

This command stops the lab and removes the containers and networks without deleting any files.