# Edge clusters

As a User I would like to start k8s clusters in edge locations. 

Benefits: We can make this downloadable so people can play with it at home in their free time. Eg a tutorial how to install this at home and deploy and manage home automation apps via our app platform

Challenges: How do we connect edge clusters with our management cluster?

Here are a few details of what I researched. Raspberry Pis are not the platform that it has to be, ARM also isn’t necessarily. But first of all it was what I have here and I would like to have a reference POC installation available as quickly as possible. In addition, you could pack the setup relatively easily in a 3D printed case and build a small appliance from it.

I’ve run k3s here. The main problem is that it currently have is installed on SD cards and that the setup is a snowflake installation. So the main point that I missed was to set up a management cluster that can be provisioned and configured declaratively. SD cards are also prone to problems if you boot hard or if the power fails. Yes, you could do it with USB disks, but that doesn't solve the snowflake problem.

In general I like the idea of a control plane appliance with rather simple and cheap components. This makes edge locations easier to scale. We can iterate over the design, switch out the control planes over time as the hardware is inexpensive. We would have more control over the whole stack. Repeatability is key.

## Bastion

I currently have a bastion with wireguard, dnsmasq and matchbox[1]. Very similar to our on-prem setup, but I used matchbox as an alternative to Mayu. This is the former bootcfg from CoreOS and is still used in the Poseidon Kubernetes distribution. It could very well be that we will also be using this for our on-prem setup. The Bastion is still a snowflake, as in the on-prem setup. I don't have many ideas for that yet. The SD card could be made read-only. This would prevent file system corruption and the SD card would last longer. Writes can be activated temporarily for upgrades. We could even put this in a firmware on a smaller device instead of using a full blown linux for this. I still have to think about logs. Possibly streaming to the cloud. You could also put a registry cache on it. Maybe with a USB SSD. The RPi can now boot directly from there. The SD card could contain an emergency system that is really read-only. There are also UPS shields for the RPi[2].

## Provisioning

The Bastion can provision the Raspberry Pis for the Control Plane Cluster with Flatcar arm64[3]. Raspberry PI 4 can be booted in the firmware via PXE. However, I couldn't manage the iPXE chainloading. That's why I stumbled across a new UEFI RPi firmware [4]. Based on Tianoncore and is an open source implementation of Intel's UEFI. Pretty awesome and the timing seems good. Booted my PIs with it and that slowly turns the RPi into a server. iPXE already works. An active member has a Vagrant Build Environment on Github [5] to compile iPXE for ARM. He's already using it and is active in some issues. The Bastion can switch the power of the individual RPis via a relay. That's not hard. I’ve configured dnsmasq to only do PXE boot but leave managing IP ranges to my home router. Might also be important in general as we shouldn’t expect that an edge location rebuilds their whole network just for our control plane.

## State

The RPi master gets an SSD for the Etcd state via USB. State for the control plane is still to be determined. I am thinking mainly about logs and metrics here. There is not much else that needs disks on a control plane. We could attach USB SSDs to each RPi and then put rook on top might be something to look at after Team Rocket went with a decision for the on-prem setups in general

## Other random thoughts

For the casing of a POC I can definitely come up with a 3D design with our Logo etc.

A first POC might have too many components or isn’t rugged enough. I’d first focus on the concept and to make it work. Later on we can optimize. We could even build special hardware if we want. 

In case of remote management of IPMI I stumbled upon pikvm[6]. Might also be worth to look into for the management of the physical machines.

We need to look into how we can separate the networks a bit for security reasons. Eg PXE, Management Cluster, the Cluster and Ingress. In general we would need to make Ingress as simple as possible. 

## Installation

Activate PXE boot in firmware (this isn’t necessary with UEFI and ipxe)
Via https://www.raspberrypi.org/documentation/hardware/raspberrypi/bcm2711_bootloader_config.md

I already had an archlinux on an SD card to modify the firmware on the RPis. But this step isn’t necessary at all if we get ipxe via UEFI to work.

```
# install rpi-eeprom
sudo pacman -S git patch fakeroot binutils
git clone https://aur.archlinux.org/rpi-eeprom.git
cd rpi-eeprom
makepkg -i

# firmware upgrade
sudo rpi-eeprom-update -a
sudo reboot

# default to network boot
sudo -E rpi-eeprom-config /lib/firmware/raspberrypi/bootloader/critical/pieeprom-2020-04-16.bin  > bootloader.config

cat bootloader.config
[all]
BOOT_UART=0
WAKE_ON_GPIO=1
POWER_OFF_ON_HALT=0
DHCP_TIMEOUT=45000
DHCP_REQ_TIMEOUT=4000
TFTP_FILE_TIMEOUT=30000
TFTP_IP=192.168.1.31
TFTP_PREFIX=0
BOOT_ORDER=0xf12
SD_BOOT_MAX_RETRIES=3
NET_BOOT_MAX_RETRIES=5
[none]
FREEZE_VERSION=0

sudo -E rpi-eeprom-config --config bootloader.config /lib/firmware/raspberrypi/bootloader/critical/pieeprom-2020-04-16.bin  --out pieeprom-2020-12-02.bin

sudo rpi-eeprom-update -d -f ./pieeprom-2020-12-02.bin
sudo reboot
```

### Install matchbox

Via https://github.com/poseidon/matchbox/blob/master/docs/deployment.md

Matchbox is installed on a separate RPi that becomes the bastion. Currently I use a raspbian buster RPi for that.

```
# matchbox
wget https://github.com/poseidon/matchbox/releases/download/v0.9.0/matchbox-v0.9.0-linux-arm.tar.gz
wget https://github.com/poseidon/matchbox/releases/download/v0.9.0/matchbox-v0.9.0-linux-arm.tar.gz.asc
gpg --keyserver keyserver.ubuntu.com --recv-key 2E3D92BF07D9DDCCB3BAE4A48F515AD1602065C8
gpg --verify matchbox-v0.9.0-linux-arm.tar.gz.asc matchbox-v0.9.0-linux-arm.tar.gz
tar xzvf matchbox-v0.9.0-linux-arm.tar.gz
cd matchbox-v0.9.0-linux-arm
sudo cp matchbox /usr/local/bin
sudo useradd -U matchbox
sudo mkdir -p /var/lib/matchbox/assets
sudo chown -R matchbox:matchbox /var/lib/matchbox
sudo cp contrib/systemd/matchbox.service /etc/systemd/system/matchbox.service
sudo systemctl edit matchbox
[Service]
Environment="MATCHBOX_ADDRESS=0.0.0.0:8080"
Environment="MATCHBOX_RPC_ADDRESS=0.0.0.0:8081"
sudo systemctl daemon-reload
sudo systemctl start matchbox
sudo systemctl enable matchbox

# matchbox tls
cd scripts/tls
export SAN=DNS.1:matchbox.home.derstappen.com,IP.1:192.168.1.31
./cert-gen
sudo mkdir -p /etc/matchbox
sudo cp ca.crt server.crt server.key /etc/matchbox
sudo chown -R matchbox:matchbox /etc/matchbox
mkdir -p ~/.matchbox
cp client.crt client.key ca.crt ~/.matchbox/

# download flatcar
vim ./scripts/get-flatcar (change amd64 to arm64)
./scripts/get-flatcar alpha 2705.0.0
sudo mv examples/assets/flatcar /var/lib/matchbox/assets
sudo chown -R matchbox:matchbox /var/lib/matchbox/

# install dnsmasq for pxe (not fully necessary if we do ipxe via SD card)

apt install dnsmasq
cat /etc/dnsmasq.d/pxe.conf
log-dhcp
port=0
enable-tftp
dhcp-no-override
dhcp-range=192.168.1.31,proxy
tftp-root=/var/lib/tftpboot

# Legacy PXE
dhcp-match=set:bios,option:client-arch,0
dhcp-boot=tag:bios,undionly.kpxe

# UEFI
dhcp-match=set:efi32,option:client-arch,6
dhcp-boot=tag:efi32,ipxe.efi

dhcp-match=set:efibc,option:client-arch,7
dhcp-boot=tag:efibc,ipxe.efi

dhcp-match=set:efi64,option:client-arch,9
dhcp-boot=tag:efi64,ipxe.efi

# iPXE
dhcp-userclass=set:ipxe,iPXE
dhcp-boot=tag:ipxe,http://matchbox.home.derstappen.com:8080/boot.ipxe

log-queries
log-dhcp

mkdir -p /var/lib/tftproot
cd /var/lib/tftproot
sudo curl -s -o undionly.kpxe http://boot.ipxe.org/undionly.kpxe
sudo cp undionly.kpxe undionly.kpxe.0
sudo curl -s -o ipxe.efi http://boot.ipxe.org/ipxe.efi
```

## Next steps

Next I have to think about how to install a cluster on physical machines via the control plane. So probably again iPXE and an operator who takes over the matchbox configuration and can start machines. I'll go a little further and then have to see if I can find a few people internally who will build a POC with me in a task force.

There was a talk on last rejekts in the US from a company called Volterra about how they are managing edge clusters. k8s part wasn't super interesting (they pack everything into a single binary similarly to k3s), but the way networking is done is pretty decent. talk recording https://www.youtube.com/watch?v=Sz_RCstTlE0

* [1] https://github.com/poseidon/matchbox/
* [2] https://www.conrad.de/de/p/joy-it-rb-strompi3bat-xl-raspberry-pi-usv-passend-fuer-einplatinen-computer-raspberry-pi-2205374.html, https://www.conrad.de/de/p/joy-it-strompi-3-usv-shield-passend-fuer-raspberry-pi-1611052.html
* [3] https://alpha.release.flatcar-linux.net/arm64-usr/current/
* [4] https://rpi4-uefi.dev/
* [5] https://github.com/rgl/raspberrypi-uefi-edk2-vagrant
* [6] https://github.com/pikvm/pikvm
