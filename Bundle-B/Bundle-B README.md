**Bundle B Python Testing:**
This python program supports user management and monitoring users using NetBird Cloud. It retrieves user information such as email and museum role. There are three main features of this program:

1) List Users - Displays usernames, emails and museum roles. 
2) View Groups - Displays the groups.
3) Check User Access - Checks a users role via email.

How to Run:
1. Open the terminal and go into Bundle-B directory
2. Run python user_management.py
3. Enter private API token when prompted.
4. Select an option from menu.
5. Exit.

**Bundle B NetBird Local Access Testing:**

**1. Architecture**

Museum-Server: Contains the peer(s) acting as the server (for example, ‘Kanagxx’ at ‘100.89.153.83’)

Three Pre-Assigned Setup Keys: Instand of manually toggling peer groups during testing, setup keys are configured with autoassigned groups so each test container automatically joins its intended role upon startup:
1) Staff Setup Key (`Staff`): Auto-assigns the `Staff` group.
2) Volunteer Setup Key (`Volunteers`): Auto-assigns the `Volunteers` group.
3) Blocked / Revoked Setup Key (None): Auto-assigns no role groups.

Policies:
Staff Full Access: `Staff --> Museum-Server` (allowed across protocols/ports).
Volunteer Web-Only Policy: `Volunteers --> Museum-Server` (allowed only on configured web TCP ports 80).


**2. Permissions & Prerequisites**

   Admin / Owner Boundaries: Only the NetBird admins can edit groups or Access Control policies in NetBird Cloud. But because the three test setup keys automatically assign groups at container startup, individuals do not need NetBird admin permissions to test `Staff`, `Volunteers`, or `Blocked` access.
   

Target Server Requirement: Whichever machine hosts the test web server (`python -m http.server 80`) must already be assigned to **`Museum-Server`** in NetBird Cloud (with `Staff` and `Volunteers` removed from that server peer during testing so its own role does not mess with results).
   Tools Needed: Docker Desktop, Two PowerShell terminals, and Python 3.

    
      Staff Setup Key:
      3700AB66-762D-48E6-9C33-88F3BED8336D

      Volunteer Setup Key:
      9E2A14D1-F3EA-4285-8C1E-2943CF739C3B

      Blocked/Revoked Setup Key:
      6DBE14B0-1C9A-4D3B-83AA-1C5A22250BAC

**3. Steps to Test:**

 1) On the machine assigned to ’Museum-Server’ group (ex: ‘Kanagxx’ at ‘100.89.153.83’ or  ‘RoseN’ at ‘100.89.68.104’), open powershell and start a HTTP server on port 80:
    
        python -m http.server 80


 2) In a second powershell terminal, start the three testers:

        docker run -d --name staff-test-peer --cap-add=NET_ADMIN -e NB_SETUP_KEY= 3700AB66-762D-48E6-9C33-88F3BED8336D netbirdio/netbird:latest

        docker run -d --name volunteer-test-peer --cap-add=NET_ADMIN -e NB_SETUP_KEY=9E2A14D1-F3EA-4285-8C1E-2943CF739C3B netbirdio/netbird:latest

        docker run -d --name revoked-test-peer --cap-add=NET_ADMIN -e NB_SETUP_KEY=6DBE14B0-1C9A-4D3B-83AA-1C5A22250BAC netbirdio/netbird:latest

 3) Run the Staff Access Test using your NetBird machine’s own IP address

         docker exec netbird-test-peer wget -T 3 -q0 http:// <YOUR-NETBIRD-IP-ADDRESS>  
(ex: docker exec netbird-test-peer wget -T 3 -qO- http://100.89.153.83)


 4) Run the Volunteer Access Test on port 80 using your NetBird machine’s own IP address

        docker exec volunteer-test-peer wget -T 3 -q0 http:// <YOUR-NETBIRD-IP-ADDRESS>  
(ex: docker exec volunteer-test-peer wget -T 3 -qO- http://100.89.153.83)


 5) Run the Volunteer Access Test using a different port 

        docker exec volunteer-test-peer wget -T 3 -q0 http:// <YOUR-NETBIRD-IP-ADDRESS>:8080

(ex:docker exec volunteer-test-peer wget -T 3 -qO- http://100.89.153.83:8080)


 6) Run the Blocked-Tester

        docker exec revoked-test-peer wget -T 3 -qO- http://<YOUR-NETBIRD-IP-ADDRESS>  
(ex: docker exec revoked-test-peer wget -T 3 -qO- http://100.89.153.83)


 7) Remove the temporary docker tests

        docker rm -f netbird-test-peer volunteer-test-peer revoked-test-peer


