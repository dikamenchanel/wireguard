#!/bin/bash

sudo apt install wireguard;

if [ ! -d ~/wg ]; then
	mkdir wg;
fi

# get root
#sudo -i
#D=wg_user_conf
# change diractroy

sudo apt install curl;

cd  ~/wg

path_conf=/etc/wireguard
FILE=/etc/wireguard/wg0.conf
if [ ! -f $FILE  ]; then

	# Generation keys for wireguard server  private and public
	sudo wg genkey | sudo  tee  $path_conf/privatekey | sudo wg pubkey | sudo tee $path_conf/publickey;
	sudo chmod 600 $path_conf/privatekey
	sudo touch $path_conf/data
	sudo chmod 600 $path_conf/data
	# Create your User | How will call him ?
	echo " Name your user:"
	read user

	# Generation keys for user
	wg genkey | tee ./"$user"_privatekey | wg pubkey | tee ./"$user"_publickey

	# Varibles  for configurate wireguard server
	SERVER_IP=$(curl -s ifconfig.me)
	public=$(sudo cat $path_conf/publickey);
	private=$(sudo cat $path_conf/privatekey);
	user_publickey=$(cat "$user"_publickey)
	user_privatekey=$(cat "$user"_privatekey)
	echo " What allow port (default 51820):"
	read port
	if [[ $port ]];  then
		port=$port
	else
		port="51820"
	fi
	# Сreate file and write out  commands in file configurate

	sudo touch $path_conf/wg0.conf;
	echo -e "[Interface]" | sudo tee -a $path_conf/wg0.conf;
	echo -e "PrivateKey = $private " | sudo tee -a $path_conf/wg0.conf;
	echo -e "Address = 10.0.0.1/24 " | sudo tee -a $path_conf/wg0.conf;
	echo -e "ListenPort = $port " | sudo tee -a $path_conf/wg0.conf;
	net_face=$(ip -o -4 route show to default | awk '{print $5}')

	echo -e "PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o $net_face -j MASQUERADE" | sudo tee -a $path_conf/wg0.conf;
	echo -e "PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o $net_face -j MASQUERADE \n" | sudo tee -a $path_conf/wg0.conf;

	echo -e "[Peer]" | sudo tee -a $path_conf/wg0.conf;

	echo -e "PublicKey = $user_publickey" | sudo tee -a $path_conf/wg0.conf;
	echo -e "Issued for the first client ip / '10.0.0.2/32':"
	ip=10.0.0.2/32
	echo -e "AllowedIPs = $ip \n " | sudo tee -a $path_conf/wg0.conf;

	echo -e "$port" |sudo tee -a $path_conf/data;

	echo -e "$ip" | sudo tee -a $path_conf/data;


	echo -e "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
	sysctl -p

	# Forwarding a port through the firewall
	sudo ufw allow "$port"/udp

	# Turn on the service in systemd
	sudo systemctl enable wg-quick@wg0.service

	# Restart service
	sudo systemctl start wg-quick@wg0.service


	# Create and write Users file configurate

	touch "$user".conf
	echo -e "[Interface]" >> "$user".conf
	echo -e "PrivateKey = $user_privatekey" >> "$user".conf
	echo -e "Address = $ip" >> "$user".conf
	echo -e "DNS = 8.8.8.8 \n" >> "$user".conf
	echo -e "[Peer]" >> "$user".conf
	echo -e "PublicKey = $public" >> "$user".conf
	echo -e "Endpoint = $SERVER_IP:$port" >> "$user".conf
	echo -e "AllowedIPs = 0.0.0.0/0" >> "$user".conf
	echo -e "PersistentKeepalive = 20" >> "$user".conf

	# Download user config file
	#scp -r $USER@$SERVER_IP:/etc/wireguard/"$user".conf ~/"$user".conf
else

	# Create your User | How will call him ?
	echo -e "Name your next user:"
	read user
	if [ ! -f "$user".conf ] ; then

	# Generation keys for user
	wg genkey | tee ./"$user"_privatekey | wg pubkey | tee ./"$user"_publickey

	# Varibles  for configurate wireguard server
	SERVER_IP=$(curl -s ifconfig.me)
	public=$(sudo cat $path_conf/publickey);
	user_privatekey=$(cat "$user"_privatekey)
	user_publickey=$(cat "$user"_publickey)
	port=$(sudo head -1 $path_conf/data)
	prev_ip=$(sudo sed '1d' $path_conf/data)

	# Add strings  out  commands in file configurate WireGuard Server

	echo -e "[Peer]" | sudo tee -a $path_conf/wg0.conf
	echo -e "PublicKey = $user_publickey" | sudo tee -a $path_conf/wg0.conf
	echo -e "The previous ip was '$prev_ip'"
	echo -e " What is ip your client/ exemple(10.0.0.3/32)"
	read new_ip

	new_ip="10.0.0.$new_ip/32"
	if [ $new_ip \<  $prev_ip ]  ; then
		echo -e " This one was already there, please enter another one:"
		read ip
		new_ip="10.0.0.$ip/32"
	elif [ $new_ip =  $prev_ip  ] ; then
		echo -e " This one was already there, please enter another one:"
        	read ip
                new_ip="10.0.0.$ip/32"
	fi

	echo -e "AllowedIPs = $new_ip \n" | sudo tee -a $path_conf/wg0.conf
	sudo rm $path_conf/data
	echo  $port  |sudo tee -a $path_conf/data
	echo $new_ip |sudo tee -a $path_conf/data

	sudo chmod 600 $path_conf/data

	# Restart Service
	sudo systemctl restart wg-quick@wg0.service

	# Create and write Users file configurate 
	touch "$user".conf
	echo -e "[Interface]" >> "$user".conf
	echo -e "PrivateKey = $user_privatekey" >> "$user".conf
	echo -e "Address = $new_ip" >> "$user".conf
	echo -e "DNS = 8.8.8.8 \n " >> "$user".conf
	echo -e "[Peer]" >> "$user".conf
	echo -e "PublicKey = $public" >> "$user".conf
	echo -e "Endpoint = $SERVER_IP:$port" >> "$user".conf
	echo -e "AllowedIPs = 0.0.0.0/0" >> "$user".conf
	echo -e "PersistentKeepalive = 20" >> "$user".conf

	# Download user config file
	#scp -r $USER@$SERVER_IP:/etc/wireguard/"$user".conf ~/"$user".conf
	else
		echo -e " The user '$user' already exists, please update the script again!"

	fi
fi

echo -e " The end!"
