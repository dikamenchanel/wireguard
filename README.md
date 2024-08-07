 # wireguard
это сценарий bash для настройки wireguard Free VPN server

# WireGuard Installation Script

This script installs WireGuard, sets up server and peer configurations, and starts the WireGuard service.

## Steps to Use

1. **Clone the Repository**

    Download the script from the repository:

    ```bash
    git clone https://github.com/dikamenchanel/wireguard.git
    ```

2. **Change Directory**

    change directory:

    ```bash
    cd wireguard
    ```
    
3. **Make the Script Executable**

    Make the script executable by running:

    ```bash
    chmod +x wg-setup.py
    ```
    
4. **Run the Script as Superuser**

    Run the script with superuser privileges to install WireGuard and set up the configurations:

    ```bash
    sudo ./wg-setup.py
    ```

5. **Optional: Move the Script to /usr/bin**

    If you want to be able to run the script from anywhere, you can move it to `/usr/bin`:

    ```bash
    sudo mv wg-setup.py /usr/bin/wg-setup
    ```

## Notes

- Ensure you have the necessary permissions to move the script to `/usr/bin` and run it with superuser privileges.
- The script will prompt you for necessary inputs, such as the server port and peer configuration details.
- **Repeatable Use**: Running the script again will offer the option to create a new peer configuration, making the script reusable for adding multiple peers.
