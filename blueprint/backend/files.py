"""
Search for configuration files to include in the blueprint.
"""

import base64
from collections import defaultdict
import errno
import glob
import grp
import hashlib
import logging
import os.path
import pwd
import re
import stat
import subprocess

from blueprint import util


# An extra list of pathnames and MD5 sums that will be checked after no
# match is found in `dpkg`(1)'s list.  If a pathname is given as the value
# then that file's contents will be hashed.
#
# Many of these files are distributed with packages and copied from
# `/usr/share` in the `postinst` program.
#
# XXX Update `blueprintignore`(5) if you make changes here.
MD5SUMS = {'/etc/adduser.conf': ['/usr/share/adduser/adduser.conf'],
           '/etc/apparmor.d/tunables/home.d/ubuntu':
               ['2a88811f7b763daa96c20b20269294a4'],
           '/etc/apt/apt.conf.d/00CDMountPoint':
               ['cb46a4e03f8c592ee9f56c948c14ea4e'],
           '/etc/apt/apt.conf.d/00trustcdrom':
               ['a8df82e6e6774f817b500ee10202a968'],
           '/etc/chatscripts/provider': ['/usr/share/ppp/provider.chatscript'],
           '/etc/default/console-setup':
               ['0fb6cec686d0410993bdf17192bee7d6',
                'b684fd43b74ac60c6bdafafda8236ed3',
                '/usr/share/console-setup/console-setup'],
           '/etc/default/grub': ['ee9df6805efb2a7d1ba3f8016754a119',
                                 'ad9283019e54cedfc1f58bcc5e615dce'],
           '/etc/default/irqbalance': ['7e10d364b9f72b11d7bf7bd1cfaeb0ff'],
           '/etc/default/keyboard': ['06d66484edaa2fbf89aa0c1ec4989857'],
           '/etc/default/locale': ['164aba1ef1298affaa58761647f2ceba',
                                   '7c32189e775ac93487aa4a01dffbbf76'],
           '/etc/default/rcS': ['/usr/share/initscripts/default.rcS'],
           '/etc/environment': ['44ad415fac749e0c39d6302a751db3f2'],
           '/etc/hosts.allow': ['8c44735847c4f69fb9e1f0d7a32e94c1'],
           '/etc/hosts.deny': ['92a0a19db9dc99488f00ac9e7b28eb3d'],
           '/etc/initramfs-tools/modules':
               ['/usr/share/initramfs-tools/modules'],
           '/etc/inputrc': ['/usr/share/readline/inputrc'],
           '/etc/iscsi/iscsid.conf': ['6c6fd718faae84a4ab1b276e78fea471'],
           '/etc/kernel-img.conf': ['f1ed9c3e91816337aa7351bdf558a442'],
           '/etc/ld.so.conf': ['4317c6de8564b68d628c21efa96b37e4'],
           '/etc/ld.so.conf.d/nosegneg.conf':
               ['3c6eccf8f1c6c90eaf3eb486cc8af8a3'],
           '/etc/networks': ['/usr/share/base-files/networks'],
           '/etc/nsswitch.conf': ['/usr/share/base-files/nsswitch.conf'],
           '/etc/pam.d/common-account': ['9d50c7dda6ba8b6a8422fd4453722324'],
           '/etc/pam.d/common-auth': ['a326c972f4f3d20e5f9e1b06eef4d620'],
           '/etc/pam.d/common-password': ['9f2fbf01b1a36a017b16ea62c7ff4c22'],
           '/etc/pam.d/common-session': ['e2b72dd3efb2d6b29698f944d8723ab1'],
           '/etc/pam.d/common-session-noninteractive':
               ['508d44b6daafbc3d6bd587e357a6ff5b'],
           '/etc/pam.d/fingerprint-auth-ac':
               ['d851f318a16c32ed12f5b1cd55e99281'],
           '/etc/pam.d/fingerprint-auth': ['d851f318a16c32ed12f5b1cd55e99281'],
           '/etc/pam.d/password-auth-ac': ['e8aee610b8f5de9b6a6cdba8a33a4833'],
           '/etc/pam.d/password-auth': ['e8aee610b8f5de9b6a6cdba8a33a4833'],
           '/etc/pam.d/smartcard-auth-ac':
               ['dfa6696dc19391b065c45b9525d3ae55'],
           '/etc/pam.d/smartcard-auth': ['dfa6696dc19391b065c45b9525d3ae55'],
           '/etc/pam.d/system-auth-ac': ['e8aee610b8f5de9b6a6cdba8a33a4833'],
           '/etc/pam.d/system-auth': ['e8aee610b8f5de9b6a6cdba8a33a4833'],
           '/etc/ppp/chap-secrets': ['faac59e116399eadbb37644de6494cc4'],
           '/etc/ppp/pap-secrets': ['698c4d412deedc43dde8641f84e8b2fd'],
           '/etc/ppp/peers/provider': ['/usr/share/ppp/provider.peer'],
           '/etc/profile': ['/usr/share/base-files/profile'],
           '/etc/python/debian_config': ['7f4739eb8858d231601a5ed144099ac8'],
           '/etc/rc.local': ['10fd9f051accb6fd1f753f2d48371890'],
           '/etc/rsyslog.d/50-default.conf':
                ['/usr/share/rsyslog/50-default.conf'],
           '/etc/security/opasswd': ['d41d8cd98f00b204e9800998ecf8427e'],
           '/etc/selinux/restorecond.conf':
               ['b5b371cb8c7b33e17bdd0d327fa69b60'],
           '/etc/selinux/targeted/modules/semanage.trans.LOCK':
               ['d41d8cd98f00b204e9800998ecf8427e'],
           '/etc/selinux/targeted/modules/active/file_contexts.template':
               ['bfa4d9e76d88c7dc49ee34ac6f4c3925'],
           '/etc/selinux/targeted/modules/active/file_contexts':
               ['1622b57a3b85db3112c5f71238c68d3e'],
           '/etc/selinux/targeted/modules/active/users_extra':
               ['daab665152753da1bf92ca0b2af82999'],
           '/etc/selinux/targeted/modules/active/base.pp':
               ['6540e8e1a9566721e70953a3cb946de4'],
           '/etc/selinux/targeted/modules/active/modules/fetchmail.pp':
               ['0b0c7845f10170a76b9bd4213634cb43'],
           '/etc/selinux/targeted/modules/active/modules/usbmuxd.pp':
               ['72a039c5108de78060651833a073dcd1'],
           '/etc/selinux/targeted/modules/active/modules/pulseaudio.pp':
               ['d9c4f1abf8397d7967bb3014391f7b61'],
           '/etc/selinux/targeted/modules/active/modules/screen.pp':
               ['c343b6c4df512b3ef435f06ed6cfd8b4'],
           '/etc/selinux/targeted/modules/active/modules/cipe.pp':
               ['4ea2d39babaab8e83e29d13d7a83e8da'],
           '/etc/selinux/targeted/modules/active/modules/rpcbind.pp':
               ['48cdaa5a31d75f95690106eeaaf855e3'],
           '/etc/selinux/targeted/modules/active/modules/nut.pp':
               ['d8c81e82747c85d6788acc9d91178772'],
           '/etc/selinux/targeted/modules/active/modules/mozilla.pp':
               ['405329d98580ef56f9e525a66adf7dc5'],
           '/etc/selinux/targeted/modules/active/modules/openvpn.pp':
               ['110fe4c59b7d7124a7d33fda1f31428a'],
           '/etc/selinux/targeted/modules/active/modules/denyhosts.pp':
               ['d12dba0c7eea142c16abd1e0424dfda4'],
           '/etc/selinux/targeted/modules/active/modules/rhcs.pp':
               ['e7a6bf514011f39f277d401cd3d3186a'],
           '/etc/selinux/targeted/modules/active/modules/radius.pp':
               ['a7380d93d0ac922364bc1eda85af80bf'],
           '/etc/selinux/targeted/modules/active/modules/policykit.pp':
               ['1828a7a89c5c7a9cd0bd1b04b379e2c0'],
           '/etc/selinux/targeted/modules/active/modules/varnishd.pp':
               ['260ef0797e6178de4edeeeca741e2374'],
           '/etc/selinux/targeted/modules/active/modules/bugzilla.pp':
               ['c70402a459add46214ee370039398931'],
           '/etc/selinux/targeted/modules/active/modules/java.pp':
               ['ac691d90e755a9a929c1c8095d721899'],
           '/etc/selinux/targeted/modules/active/modules/courier.pp':
               ['d6eb2ef77d755fd49d61e48383867ccb'],
           '/etc/selinux/targeted/modules/active/modules/userhelper.pp':
               ['787e5ca0ee1c9e744e9116837d73c2b9'],
           '/etc/selinux/targeted/modules/active/modules/sssd.pp':
               ['aeb11626d9f34af08e9cd50b1b5751c7'],
           '/etc/selinux/targeted/modules/active/modules/munin.pp':
               ['db2927d889a3dfbe439eb67dfdcba61d'],
           '/etc/selinux/targeted/modules/active/modules/ppp.pp':
               ['7c6f91f4aae1c13a3d2a159a4c9b8553'],
           '/etc/selinux/targeted/modules/active/modules/xfs.pp':
               ['6b3be69f181f28e89bfcffa032097dcb'],
           '/etc/selinux/targeted/modules/active/modules/consolekit.pp':
               ['ef682e07a732448a12f2e93da946d655'],
           '/etc/selinux/targeted/modules/active/modules/telnet.pp':
               ['43fd78d022e499bcb6392da33ed6e28d'],
           '/etc/selinux/targeted/modules/active/modules/nagios.pp':
               ['9c9e482867dce0aa325884a50a023a83'],
           '/etc/selinux/targeted/modules/active/modules/sysstat.pp':
               ['0fc4e6b3472ce5e8cfd0f3e785809552'],
           '/etc/selinux/targeted/modules/active/modules/tor.pp':
               ['2c926e3c5b79879ed992b72406544394'],
           '/etc/selinux/targeted/modules/active/modules/qpidd.pp':
               ['959d4763313e80d8a75bc009094ea085'],
           '/etc/selinux/targeted/modules/active/modules/radvd.pp':
               ['a7636d3df0f431ad421170150e8a9d2e'],
           '/etc/selinux/targeted/modules/active/modules/aiccu.pp':
               ['c0eafc1357cd0c07be4034c1a27ada98'],
           '/etc/selinux/targeted/modules/active/modules/tgtd.pp':
               ['55da30386834e60a10b4bab582a1b689'],
           '/etc/selinux/targeted/modules/active/modules/sectoolm.pp':
               ['6f8fba8d448da09f85a03622de295ba9'],
           '/etc/selinux/targeted/modules/active/modules/unconfineduser.pp':
               ['0bc2f6faf3b38a657c4928ec7b611d7a'],
           '/etc/selinux/targeted/modules/active/modules/sambagui.pp':
               ['31a5121c80a6114b25db4984bdf8d999'],
           '/etc/selinux/targeted/modules/active/modules/mpd.pp':
               ['cdabce7844a227a81c2334dec0c49e9b'],
           '/etc/selinux/targeted/modules/active/modules/hddtemp.pp':
               ['76d85610a7e198c82406d850ccd935e1'],
           '/etc/selinux/targeted/modules/active/modules/clamav.pp':
               ['f8f5b60e3f5b176810ea0666b989f63d'],
           '/etc/selinux/targeted/modules/active/modules/tvtime.pp':
               ['886dc0a6e9ebcbb6787909851e7c209f'],
           '/etc/selinux/targeted/modules/active/modules/cgroup.pp':
               ['9e1cd610b6fde0e9b42cabd7f994db46'],
           '/etc/selinux/targeted/modules/active/modules/rshd.pp':
               ['e39cec5e9ade8a619ecb91b85a351408'],
           '/etc/selinux/targeted/modules/active/modules/roundup.pp':
               ['133b9b3b2f70422953851e18d6c24276'],
           '/etc/selinux/targeted/modules/active/modules/virt.pp':
               ['9ae34fca60c651c10298797c1260ced0'],
           '/etc/selinux/targeted/modules/active/modules/asterisk.pp':
               ['f823fdcb2c6df4ddde374c9edb11ef26'],
           '/etc/selinux/targeted/modules/active/modules/livecd.pp':
               ['8972e6ef04f490b8915e7983392b96ce'],
           '/etc/selinux/targeted/modules/active/modules/netlabel.pp':
               ['91fc83e5798bd271742823cbb78c17ff'],
           '/etc/selinux/targeted/modules/active/modules/qemu.pp':
               ['e561673d5f9e5c19bcae84c1641fa4a7'],
           '/etc/selinux/targeted/modules/active/modules/unconfined.pp':
               ['3acd5dceb6b7a71c32919c29ef920785'],
           '/etc/selinux/targeted/modules/active/modules/postgresql.pp':
               ['3ecc9f2c7b911fa37d8ab6cc1c6b0ea7'],
           '/etc/selinux/targeted/modules/active/modules/apache.pp':
               ['c0089e4472399e9bc5237b1e0485ac39'],
           '/etc/selinux/targeted/modules/active/modules/abrt.pp':
               ['09e212789d19f41595d7952499236a0c'],
           '/etc/selinux/targeted/modules/active/modules/rsync.pp':
               ['e2567e8716c116ea6324c77652c97137'],
           '/etc/selinux/targeted/modules/active/modules/git.pp':
               ['7904fd9fbae924be5377ccd51036248e'],
           '/etc/selinux/targeted/modules/active/modules/amanda.pp':
               ['594eddbbe3b4530e79702fc6a882010e'],
           '/etc/selinux/targeted/modules/active/modules/cvs.pp':
               ['62cf7b7d58f507cc9f507a6c303c8020'],
           '/etc/selinux/targeted/modules/active/modules/chronyd.pp':
               ['a4ff3e36070d461771230c4019b23440'],
           '/etc/selinux/targeted/modules/active/modules/gpm.pp':
               ['ed3f26e774be81c2cbaaa87dcfe7ae2d'],
           '/etc/selinux/targeted/modules/active/modules/modemmanager.pp':
               ['840d4da9f32a264436f1b22d4d4a0b2a'],
           '/etc/selinux/targeted/modules/active/modules/podsleuth.pp':
               ['67e659e9554bc35631ee829b5dc71647'],
           '/etc/selinux/targeted/modules/active/modules/publicfile.pp':
               ['0f092d92c326444dc9cee78472c56655'],
           '/etc/selinux/targeted/modules/active/modules/postfix.pp':
               ['a00647ad811c22810c76c1162a97e74b'],
           '/etc/selinux/targeted/modules/active/modules/exim.pp':
               ['8c3cd1fbd8f68e80ac7707f243ac1911'],
           '/etc/selinux/targeted/modules/active/modules/telepathy.pp':
               ['9b32f699beb6f9c563f06f6b6d76732c'],
           '/etc/selinux/targeted/modules/active/modules/amtu.pp':
               ['1b87c9fef219244f80b1f8f57a2ce7ea'],
           '/etc/selinux/targeted/modules/active/modules/bitlbee.pp':
               ['cf0973c8fff61577cf330bb74ef75eed'],
           '/etc/selinux/targeted/modules/active/modules/memcached.pp':
               ['0146491b4ab9fbd2854a7e7fb2092168'],
           '/etc/selinux/targeted/modules/active/modules/sandbox.pp':
               ['82502d6d11b83370d1a77343f20d669f'],
           '/etc/selinux/targeted/modules/active/modules/dictd.pp':
               ['6119d37987ea968e90a39d96866e5805'],
           '/etc/selinux/targeted/modules/active/modules/pingd.pp':
               ['16c40af7785c8fa9d40789284ce8fbb9'],
           '/etc/selinux/targeted/modules/active/modules/milter.pp':
               ['acaec7d2ee341e97ac5e345b55f6c7ae'],
           '/etc/selinux/targeted/modules/active/modules/snort.pp':
               ['25f360aa5dec254a8fc18262bbe40510'],
           '/etc/selinux/targeted/modules/active/modules/cups.pp':
               ['5323d417895d5ab508048e2bc45367bf'],
           '/etc/selinux/targeted/modules/active/modules/rdisc.pp':
               ['5bed79cb1f4d5a2b822d6f8dbf53fe97'],
           '/etc/selinux/targeted/modules/active/modules/rlogin.pp':
               ['6f88cc86985b4bc79d4b1afbffb1a732'],
           '/etc/selinux/targeted/modules/active/modules/openct.pp':
               ['884f078f5d12f7b1c75cf011a94746e1'],
           '/etc/selinux/targeted/modules/active/modules/dbskk.pp':
               ['caa93f24bfeede892fd97c59ee8b61da'],
           '/etc/selinux/targeted/modules/active/modules/bluetooth.pp':
               ['ce4f1b34168c537b611783033316760e'],
           '/etc/selinux/targeted/modules/active/modules/gpsd.pp':
               ['dd15485b8c6e5aeac018ddbe0948464c'],
           '/etc/selinux/targeted/modules/active/modules/tuned.pp':
               ['5fc9de20402245e4a1a19c5b31101d06'],
           '/etc/selinux/targeted/modules/active/modules/piranha.pp':
               ['fcedf8588c027633bedb76b598b7586f'],
           '/etc/selinux/targeted/modules/active/modules/vhostmd.pp':
               ['0ca7152ed8a0ae393051876fe89ed657'],
           '/etc/selinux/targeted/modules/active/modules/corosync.pp':
               ['20518dface3d23d7408dd56a51c8e6e1'],
           '/etc/selinux/targeted/modules/active/modules/clogd.pp':
               ['533994a32ecf847a3162675e171c847c'],
           '/etc/selinux/targeted/modules/active/modules/samba.pp':
               ['c7cd9b91a5ba4f0744e3f55a800f2831'],
           '/etc/selinux/targeted/modules/active/modules/howl.pp':
               ['fef7dd76a97921c3e5e0e66fbac15091'],
           '/etc/selinux/targeted/modules/active/modules/shutdown.pp':
               ['55f36d9820dcd19c66729d446d3ce6b2'],
           '/etc/selinux/targeted/modules/active/modules/oddjob.pp':
               ['54d59b40e7bc0dc0dee3882e6c0ce9f3'],
           '/etc/selinux/targeted/modules/active/modules/pcscd.pp':
               ['e728f332850dfcb5637c4e8f220af2fc'],
           '/etc/selinux/targeted/modules/active/modules/canna.pp':
               ['de4f1a3ada6f9813da36febc31d2a282'],
           '/etc/selinux/targeted/modules/active/modules/arpwatch.pp':
               ['0ddc328fa054f363a035ba44ec116514'],
           '/etc/selinux/targeted/modules/active/modules/seunshare.pp':
               ['64844bbf79ee23e087a5741918f3a7ad'],
           '/etc/selinux/targeted/modules/active/modules/rhgb.pp':
               ['c9630cc5830fcb4b775985c5740f5a71'],
           '/etc/selinux/targeted/modules/active/modules/prelude.pp':
               ['2b85511c571c19751bb79b288267661c'],
           '/etc/selinux/targeted/modules/active/modules/portmap.pp':
               ['231abe579c0370f49cac533c6057792b'],
           '/etc/selinux/targeted/modules/active/modules/logadm.pp':
               ['980b1345ef8944a90b6efdff0c8b3278'],
           '/etc/selinux/targeted/modules/active/modules/ptchown.pp':
               ['987fc8a6ff50ef7eed0edc79f91b1ec5'],
           '/etc/selinux/targeted/modules/active/modules/vmware.pp':
               ['8cf31ec8abd75f2a6c56857146caf5a1'],
           '/etc/selinux/targeted/modules/active/modules/portreserve.pp':
               ['0354f017b429dead8de0d143f7950fcc'],
           '/etc/selinux/targeted/modules/active/modules/awstats.pp':
               ['c081d3168b28765182bb4ec937b4c0b1'],
           '/etc/selinux/targeted/modules/active/modules/tmpreaper.pp':
               ['ac0173dd09a54a87fdcb42d3a5e29442'],
           '/etc/selinux/targeted/modules/active/modules/postgrey.pp':
               ['68013352c07570ac38587df9fb7e88ee'],
           '/etc/selinux/targeted/modules/active/modules/tftp.pp':
               ['a47fb7872bfb06d80c8eef969d91e6f9'],
           '/etc/selinux/targeted/modules/active/modules/rgmanager.pp':
               ['1cee78e1ff3f64c4d013ce7b820e534b'],
           '/etc/selinux/targeted/modules/active/modules/aisexec.pp':
               ['95e70fd35e9cb8284488d6bf970815b7'],
           '/etc/selinux/targeted/modules/active/modules/xguest.pp':
               ['d8df4b61df93008cd594f98c852d4cba'],
           '/etc/selinux/targeted/modules/active/modules/cobbler.pp':
               ['6978d8b37b1da384130db5c5c2144175'],
           '/etc/selinux/targeted/modules/active/modules/mysql.pp':
               ['d147af479531042f13e70d72bd58a0e9'],
           '/etc/selinux/targeted/modules/active/modules/amavis.pp':
               ['7fc17b2f47c1d8226a9003df1ef67bb5'],
           '/etc/selinux/targeted/modules/active/modules/fprintd.pp':
               ['d58f18b496f69a74ece1f1b1b9432405'],
           '/etc/selinux/targeted/modules/active/modules/nis.pp':
               ['d696b167de5817226298306c79761fa2'],
           '/etc/selinux/targeted/modules/active/modules/squid.pp':
               ['3f9e075e79ec5aa59609a7ccebce0afe'],
           '/etc/selinux/targeted/modules/active/modules/smokeping.pp':
               ['98b83cac4488d7dd18c479b62dd3cf15'],
           '/etc/selinux/targeted/modules/active/modules/ktalk.pp':
               ['afe14e94861782679305c91da05e7d5e'],
           '/etc/selinux/targeted/modules/active/modules/certwatch.pp':
               ['bf13c9a642ded8354ba26d5462ddd60c'],
           '/etc/selinux/targeted/modules/active/modules/games.pp':
               ['3bcd17c07699d58bd436896e75a24520'],
           '/etc/selinux/targeted/modules/active/modules/zabbix.pp':
               ['5445ccfec7040ff1ccf3abf4de2e9a3c'],
           '/etc/selinux/targeted/modules/active/modules/rwho.pp':
               ['710e29c8e621de6af9ca74869624b9f0'],
           '/etc/selinux/targeted/modules/active/modules/w3c.pp':
               ['aea6b9518cb3fa904cc7ee82239b07c2'],
           '/etc/selinux/targeted/modules/active/modules/cyphesis.pp':
               ['dccb3f009cd56c5f8856861047d7f2ff'],
           '/etc/selinux/targeted/modules/active/modules/kismet.pp':
               ['f2d984e007275d35dd03a2d59ade507e'],
           '/etc/selinux/targeted/modules/active/modules/zosremote.pp':
               ['77a2681c4b1c3c001faeca9874b58ecf'],
           '/etc/selinux/targeted/modules/active/modules/pads.pp':
               ['76b7413009a202e228ee08c5511f3f42'],
           '/etc/selinux/targeted/modules/active/modules/avahi.pp':
               ['b59670ba623aba37ab8f0f1f1127893a'],
           '/etc/selinux/targeted/modules/active/modules/apcupsd.pp':
               ['81fae28232730a49b7660797ef4354c3'],
           '/etc/selinux/targeted/modules/active/modules/usernetctl.pp':
               ['22850457002a48041d885c0d74fbd934'],
           '/etc/selinux/targeted/modules/active/modules/finger.pp':
               ['5dd6b44358bbfabfdc4f546e1ed34370'],
           '/etc/selinux/targeted/modules/active/modules/dhcp.pp':
               ['7e63b07b64848a017eec5d5f6b88f22e'],
           '/etc/selinux/targeted/modules/active/modules/xen.pp':
               ['67086e8e94bdaab8247ac4d2e23162d1'],
           '/etc/selinux/targeted/modules/active/modules/plymouthd.pp':
               ['1916027e7c9f28430fa2ac30334e8964'],
           '/etc/selinux/targeted/modules/active/modules/uucp.pp':
               ['5bec7a345a314a37b4a2227bdfa926f1'],
           '/etc/selinux/targeted/modules/active/modules/daemontools.pp':
               ['aad7633adfc8b04e863b481deebaf14a'],
           '/etc/selinux/targeted/modules/active/modules/kdumpgui.pp':
               ['66e08b4187623fa1c535972a35ec058c'],
           '/etc/selinux/targeted/modules/active/modules/privoxy.pp':
               ['f13c986051659fa900786ea54a59ceae'],
           '/etc/selinux/targeted/modules/active/modules/unprivuser.pp':
               ['a0d128b495a6ea5da72c849ac63c5848'],
           '/etc/selinux/targeted/modules/active/modules/ada.pp':
               ['a75fd52c873e2c9326ad87f7515a664f'],
           '/etc/selinux/targeted/modules/active/modules/lircd.pp':
               ['3cc5cc5b24d40416f9d630a80005d33b'],
           '/etc/selinux/targeted/modules/active/modules/openoffice.pp':
               ['522c3ee13bc37cbe9903d00f0cbccd1d'],
           '/etc/selinux/targeted/modules/active/modules/puppet.pp':
               ['9da4c553f40f3dea876171e672168044'],
           '/etc/selinux/targeted/modules/active/modules/wine.pp':
               ['31c470eabd98c5a5dbc66ba52ad64de0'],
           '/etc/selinux/targeted/modules/active/modules/ulogd.pp':
               ['065551ea63de34a7257ecec152f61552'],
           '/etc/selinux/targeted/modules/active/modules/mplayer.pp':
               ['f889dbfa3d9ef071d8e569def835a2f3'],
           '/etc/selinux/targeted/modules/active/modules/ftp.pp':
               ['75a9f3563903eb8126ffbcc9277e1d8c'],
           '/etc/selinux/targeted/modules/active/modules/gnome.pp':
               ['b859e2d45123f60ff27a90cdb0f40e1b'],
           '/etc/selinux/targeted/modules/active/modules/ethereal.pp':
               ['8963c6b80025b27850f0cdf565e5bd54'],
           '/etc/selinux/targeted/modules/active/modules/iscsi.pp':
               ['7786cb4a84889010751b4d89c72a2956'],
           '/etc/selinux/targeted/modules/active/modules/chrome.pp':
               ['cb44c1c7b13cc04c07c4e787a259b63f'],
           '/etc/selinux/targeted/modules/active/modules/guest.pp':
               ['308d614589af73e39a22e5c741e9eecb'],
           '/etc/selinux/targeted/modules/active/modules/inn.pp':
               ['8d60592dcd3bf4d2fa97f0fefa9374ca'],
           '/etc/selinux/targeted/modules/active/modules/gitosis.pp':
               ['21c79a711157224bebba0a2cccbe8881'],
           '/etc/selinux/targeted/modules/active/modules/ksmtuned.pp':
               ['8f985e777c206d2bde3fc2ac6a28cd24'],
           '/etc/selinux/targeted/modules/active/modules/sosreport.pp':
               ['9b4780d27555e94335f80a0bb2ab4f14'],
           '/etc/selinux/targeted/modules/active/modules/ipsec.pp':
               ['68cacb8c78796957fb4a181390033b16'],
           '/etc/selinux/targeted/modules/active/modules/comsat.pp':
               ['1cecb3f5cbe24251017908e14838ee2a'],
           '/etc/selinux/targeted/modules/active/modules/gpg.pp':
               ['75358ddabb045e91010d80f1ab68307a'],
           '/etc/selinux/targeted/modules/active/modules/gnomeclock.pp':
               ['a4e74df48faab3af8f4df0fa16c65c7e'],
           '/etc/selinux/targeted/modules/active/modules/sasl.pp':
               ['5ba9be813a7dd4236fc2d37bc17c5052'],
           '/etc/selinux/targeted/modules/active/modules/vpn.pp':
               ['32ae00c287432ae5ad4f8affbc9e44fe'],
           '/etc/selinux/targeted/modules/active/modules/accountsd.pp':
               ['308057b48c6d70a45e5a603dbe625c2d'],
           '/etc/selinux/targeted/modules/active/modules/devicekit.pp':
               ['1f5a8f12ebeebfed2cfeb3ee4648dd13'],
           '/etc/selinux/targeted/modules/active/modules/psad.pp':
               ['b02f11705249c93735f019f5b97fdf7b'],
           '/etc/selinux/targeted/modules/active/modules/mono.pp':
               ['8bba1cc6826e8300c140f9c393ad07e9'],
           '/etc/selinux/targeted/modules/active/modules/cachefilesd.pp':
               ['82b93ba87b5920ecc8a7388f4cf8ea43'],
           '/etc/selinux/targeted/modules/active/modules/usbmodules.pp':
               ['20c3a57da3c1311a75a63f1c6ae91bf3'],
           '/etc/selinux/targeted/modules/active/modules/certmonger.pp':
               ['b9fe8ba6abc5204cd8eec546f5614ff5'],
           '/etc/selinux/targeted/modules/active/modules/pegasus.pp':
               ['bb0ec4379c28b196d1794d7310111d98'],
           '/etc/selinux/targeted/modules/active/modules/ntop.pp':
               ['99b46fe44ccf3c4e045dbc73d2a88f59'],
           '/etc/selinux/targeted/modules/active/modules/zebra.pp':
               ['12adcaae458d18f650578ce25e10521a'],
           '/etc/selinux/targeted/modules/active/modules/soundserver.pp':
               ['583abd9ccef70279bff856516974d471'],
           '/etc/selinux/targeted/modules/active/modules/stunnel.pp':
               ['2693ac1bf08287565c3b4e58d0f9ea55'],
           '/etc/selinux/targeted/modules/active/modules/ldap.pp':
               ['039baf0976f316c3f209a5661174a72e'],
           '/etc/selinux/targeted/modules/active/modules/fail2ban.pp':
               ['ce13513c427ff140bf988b01bd52e886'],
           '/etc/selinux/targeted/modules/active/modules/spamassassin.pp':
               ['e02232992676b0e1279c54bfeea290e3'],
           '/etc/selinux/targeted/modules/active/modules/procmail.pp':
               ['d5c58e90fac452a1a6d68cc496e7f1ae'],
           '/etc/selinux/targeted/modules/active/modules/afs.pp':
               ['6e7a4bf08dc7fa5a0f97577b913267ad'],
           '/etc/selinux/targeted/modules/active/modules/ricci.pp':
               ['8b1d44245be204907c82c3580a43901d'],
           '/etc/selinux/targeted/modules/active/modules/qmail.pp':
               ['ea08eb2172c275598d4f85c9b78182cd'],
           '/etc/selinux/targeted/modules/active/modules/ccs.pp':
               ['cad223d57f431e2f88a1d1542c2ac504'],
           '/etc/selinux/targeted/modules/active/modules/audioentropy.pp':
               ['19f6fd5e3ee2a3726a952631e993a133'],
           '/etc/selinux/targeted/modules/active/modules/ncftool.pp':
               ['c15f4833a21e9c8cd1237ee568aadcf3'],
           '/etc/selinux/targeted/modules/active/modules/nx.pp':
               ['3677983206101cfcd2182e180ef3876b'],
           '/etc/selinux/targeted/modules/active/modules/rtkit.pp':
               ['0eaae15f4c12522270b26769487a06e0'],
           '/etc/selinux/targeted/modules/active/modules/ntp.pp':
               ['141339ee3372e07d32575c6777c8e466'],
           '/etc/selinux/targeted/modules/active/modules/likewise.pp':
               ['b5f0d18f8b601e102fd9728fbb309692'],
           '/etc/selinux/targeted/modules/active/modules/aide.pp':
               ['69600bc8a529f8128666a563c7409929'],
           '/etc/selinux/targeted/modules/active/modules/nslcd.pp':
               ['5c87b1c80bdd8bbf60c33ef51a765a93'],
           '/etc/selinux/targeted/modules/active/modules/slocate.pp':
               ['fdea88c374382f3d652a1ac529fbd189'],
           '/etc/selinux/targeted/modules/active/modules/execmem.pp':
               ['44cc2d117e3bf1a33d4e3516aaa7339d'],
           '/etc/selinux/targeted/modules/active/modules/cpufreqselector.pp':
               ['7da9c9690dc4f076148ef35c3644af13'],
           '/etc/selinux/targeted/modules/active/modules/cmirrord.pp':
               ['084b532fa5ccd6775c483d757bcd0920'],
           '/etc/selinux/targeted/modules/active/modules/bind.pp':
               ['5560f5706c8c8e83d8a2ac03a85b93fb'],
           '/etc/selinux/targeted/modules/active/modules/uml.pp':
               ['a0841bc9ffca619fe5d44c557b70d258'],
           '/etc/selinux/targeted/modules/active/modules/staff.pp':
               ['bdf16ee0fa0721770aa31c52e45227c3'],
           '/etc/selinux/targeted/modules/active/modules/certmaster.pp':
               ['bc589a4f0dd49a05d52b9ffda7bdd149'],
           '/etc/selinux/targeted/modules/active/modules/webalizer.pp':
               ['c99ccad469be3c901ede9da9a87e44b2'],
           '/etc/selinux/targeted/modules/active/modules/hal.pp':
               ['c75783ec2dd49d437a242e0c69c31c96'],
           '/etc/selinux/targeted/modules/active/modules/kdump.pp':
               ['d731820c7b5bb711566ea23970106b7a'],
           '/etc/selinux/targeted/modules/active/modules/firewallgui.pp':
               ['ee3522a0072989ed08f70b03f7fd69d9'],
           '/etc/selinux/targeted/modules/active/modules/tcpd.pp':
               ['b1f7db819812da14c4e836a9d9e79980'],
           '/etc/selinux/targeted/modules/active/modules/mailman.pp':
               ['4116cbe11d943a076dd06cea91993745'],
           '/etc/selinux/targeted/modules/active/modules/smartmon.pp':
               ['45d6440b436d8ac3f042e80c392dd672'],
           '/etc/selinux/targeted/modules/active/modules/smoltclient.pp':
               ['dcfd6ecd62ee7191abda39315ec6ef1b'],
           '/etc/selinux/targeted/modules/active/modules/kerberos.pp':
               ['936533081cfbe28eb9145fde86edb4f8'],
           '/etc/selinux/targeted/modules/active/modules/lockdev.pp':
               ['e2da620d3272f296dd90bff8b921d203'],
           '/etc/selinux/targeted/modules/active/modules/automount.pp':
               ['a06d3d617c6d8c29e29ce3fb0db48c9c'],
           '/etc/selinux/targeted/modules/active/modules/webadm.pp':
               ['4ac9b2f95f8d8218ec93f001995fd8ba'],
           '/etc/selinux/targeted/modules/active/modules/pyzor.pp':
               ['c2b00c08d77d7d5a8588dd82c489e354'],
           '/etc/selinux/targeted/modules/active/modules/rssh.pp':
               ['aacef6c826e9d699e84a1dd564b68105'],
           '/etc/selinux/targeted/modules/active/modules/nsplugin.pp':
               ['0c90d308f5e956900150eb6ed84b0b54'],
           '/etc/selinux/targeted/modules/active/modules/lpd.pp':
               ['5bf17a46aa2d3e2ecc0daffcf092054e'],
           '/etc/selinux/targeted/modules/active/modules/dcc.pp':
               ['84749af337d72ba6bbbe54b013c6c62c'],
           '/etc/selinux/targeted/modules/active/modules/irc.pp':
               ['42897f214251c7ca9bc04379c4abff5e'],
           '/etc/selinux/targeted/modules/active/modules/icecast.pp':
               ['962c81fc8ef5fd49c925a2249d229d1d'],
           '/etc/selinux/targeted/modules/active/modules/dnsmasq.pp':
               ['ec4a8a50eb5806e450d97a77cbe8a8b4'],
           '/etc/selinux/targeted/modules/active/modules/jabber.pp':
               ['5a528d52f7337d44bfc867333f2b1921'],
           '/etc/selinux/targeted/modules/active/modules/remotelogin.pp':
               ['68c22a0bc6e4d5031153cf10d75ba76a'],
           '/etc/selinux/targeted/modules/active/modules/boinc.pp':
               ['a70386e9ffdaccd04cbb565e6fe5c822'],
           '/etc/selinux/targeted/modules/active/modules/mrtg.pp':
               ['7e6f395e72768d350d259c15d22a1cbb'],
           '/etc/selinux/targeted/modules/active/modules/snmp.pp':
               ['fc5166e3066504601037054874fe0487'],
           '/etc/selinux/targeted/modules/active/modules/cyrus.pp':
               ['d2e792bf111ce4a6ffdb87fe11d89d16'],
           '/etc/selinux/targeted/modules/active/modules/dovecot.pp':
               ['b716de8b77f0dfeb9212d5cf36bddfa1'],
           '/etc/selinux/targeted/modules/active/modules/cdrecord.pp':
               ['24c0325480e2f1d6cf1ce31c25d5f10a'],
           '/etc/selinux/targeted/modules/active/modules/calamaris.pp':
               ['c7ec43f01369524db32249fb755f4e7f'],
           '/etc/selinux/targeted/modules/active/modules/kerneloops.pp':
               ['2493d3308dfcd34e94308af9d5c888c3'],
           '/etc/selinux/targeted/modules/active/modules/razor.pp':
               ['06425e50a31f14cec090c30e05fb9827'],
           '/etc/selinux/targeted/modules/active/netfilter_contexts':
               ['d41d8cd98f00b204e9800998ecf8427e'],
           '/etc/selinux/targeted/modules/active/seusers.final':
               ['fdf1cdf1d373e4583ca759617a1d2af3'],
           '/etc/selinux/targeted/modules/active/file_contexts.homedirs':
               ['d7c4747704e9021ec2e16c7139fedfd9'],
           '/etc/selinux/targeted/modules/active/commit_num':
               ['c08cc266624f6409b01432dac9576ab0'],
           '/etc/selinux/targeted/modules/active/policy.kern':
               ['5398a60f820803049b5bb7d90dd6196b'],
           '/etc/selinux/targeted/modules/active/homedir_template':
               ['682a31c8036aaf9cf969093d7162960a'],
           '/etc/selinux/targeted/modules/semanage.read.LOCK':
               ['d41d8cd98f00b204e9800998ecf8427e'],
           '/etc/selinux/targeted/contexts/failsafe_context':
               ['940b12538b676287b3c33e68426898ac'],
           '/etc/selinux/targeted/contexts/virtual_domain_context':
               ['1e28f1b8e58e56a64c852bd77f57d121'],
           '/etc/selinux/targeted/contexts/removable_context':
               ['e56a6b14d2bed27405d2066af463df9f'],
           '/etc/selinux/targeted/contexts/netfilter_contexts':
               ['d41d8cd98f00b204e9800998ecf8427e'],
           '/etc/selinux/targeted/contexts/userhelper_context':
               ['53441d64f9bc6337e3aac33f05d0954c'],
           '/etc/selinux/targeted/contexts/virtual_image_context':
               ['b21a69d3423d2e085d5195e25922eaa1'],
           '/etc/selinux/targeted/contexts/securetty_types':
               ['ee2445f940ed1b33e778a921cde8ad9e'],
           '/etc/selinux/targeted/contexts/default_type':
               ['d0f63fea19ee82e5f65bdbb1de899c5d'],
           '/etc/selinux/targeted/contexts/dbus_contexts':
               ['b1c42884fa5bdbde53d64cff469374fd'],
           '/etc/selinux/targeted/contexts/files/file_contexts':
               ['1622b57a3b85db3112c5f71238c68d3e'],
           '/etc/selinux/targeted/contexts/files/file_contexts.homedirs':
               ['d7c4747704e9021ec2e16c7139fedfd9'],
           '/etc/selinux/targeted/contexts/files/media':
               ['3c867677892c0a15dc0b9e9811cc2c49'],
           '/etc/selinux/targeted/contexts/initrc_context':
               ['99866a62735a38b2bf839233c1a1689d'],
           '/etc/selinux/targeted/contexts/x_contexts':
               ['9dde3f5e3ddac42b9e99a4613c972b97'],
           '/etc/selinux/targeted/contexts/customizable_types':
               ['68be87281cf3d40cb2c4606cd2b1ea2b'],
           '/etc/selinux/targeted/contexts/users/xguest_u':
               ['e26010a418df86902332c57434370246'],
           '/etc/selinux/targeted/contexts/users/unconfined_u':
               ['ee88bed48d9601ff2b11f68f97d361ac'],
           '/etc/selinux/targeted/contexts/users/staff_u':
               ['f3412f7cbf441078a9de40fcaab93254'],
           '/etc/selinux/targeted/contexts/users/root':
               ['328e08341d1ff9296573dd43c355e283'],
           '/etc/selinux/targeted/contexts/users/user_u':
               ['2fe911f440282fda0590cd99540da579'],
           '/etc/selinux/targeted/contexts/users/guest_u':
               ['61e7e7e7403b2eac30e312342e66e4cd'],
           '/etc/selinux/targeted/contexts/default_contexts':
               ['0888c75fc814058bb3c01ef58f7a1f47'],
           '/etc/selinux/targeted/policy/policy.24':
               ['5398a60f820803049b5bb7d90dd6196b'],
           '/etc/selinux/targeted/setrans.conf':
               ['ae70362b6fa2af117bd6e293ce232069'],
           '/etc/selinux/targeted/seusers':
               ['fdf1cdf1d373e4583ca759617a1d2af3'],
           '/etc/selinux/config': ['91081ef6d958e79795d0255d7c374a56'],
           '/etc/selinux/restorecond_user.conf':
               ['4e1b5b5e38c660f87d5a4f7d3a998c29'],
           '/etc/selinux/semanage.conf': ['f33b524aef1a4df2a3d0eecdda041a5c'],
           '/etc/sgml/xml-core.cat': ['bcd454c9bf55a3816a134f9766f5928f'],
           '/etc/shells': ['0e85c87e09d716ecb03624ccff511760'],
           '/etc/ssh/sshd_config': ['e24f749808133a27d94fda84a89bb27b',
                                    '8caefdd9e251b7cc1baa37874149a870',
                                    '874fafed9e745b14e5fa8ae71b82427d'],
           '/etc/sudoers': ['02f74ccbec48997f402a063a172abb48'],
           '/etc/ufw/after.rules': ['/usr/share/ufw/after.rules'],
           '/etc/ufw/after6.rules': ['/usr/share/ufw/after6.rules'],
           '/etc/ufw/before.rules': ['/usr/share/ufw/before.rules'],
           '/etc/ufw/before6.rules': ['/usr/share/ufw/before6.rules'],
           '/etc/ufw/ufw.conf': ['/usr/share/ufw/ufw.conf']}

for pathname, overrides in MD5SUMS.iteritems():
    for i in range(len(overrides)):
        if '/' != overrides[i][0]:
            continue
        try:
            overrides[i] = hashlib.md5(open(overrides[i]).read()).hexdigest()
        except IOError:
            pass


def files(b, r):
    logging.info('searching for configuration files')

    # Visit every file in `/etc` except those on the exclusion list above.
    for dirpath, dirnames, filenames in os.walk('/etc'):

        # Determine if this entire directory should be ignored by default.
        ignored = r.ignore_file(dirpath)

        # Collect up the full pathname to each file, `lstat` them all, and
        # note which ones will probably be ignored.
        files = []
        for filename in filenames:
            pathname = os.path.join(dirpath, filename)
            try:
                files.append((pathname,
                              os.lstat(pathname),
                              r.ignore_file(pathname, ignored)))
            except OSError as e:
                logging.warning('{0} caused {1} - try running as root'.
                                format(pathname, errno.errorcode[e.errno]))

        # Track the ctime of each file in this directory.  Weed out false
        # positives by ignoring files with common ctimes.
        ctimes = defaultdict(lambda: 0)

        # Map the ctimes of each directory entry that isn't being ignored.
        for pathname, s, ignored in files:
            if not ignored:
                ctimes[s.st_ctime] += 1
        for dirname in dirnames:
            try:
                ctimes[os.lstat(os.path.join(dirpath, dirname)).st_ctime] += 1
            except OSError:
                pass

        for pathname, s, ignored in files:

            # Always ignore block special files, character special files,
            # pipes, and sockets.  They end up looking like deadlocks.
            if stat.S_ISBLK(s.st_mode) \
            or stat.S_ISCHR(s.st_mode) \
            or stat.S_ISFIFO(s.st_mode) \
            or stat.S_ISSOCK(s.st_mode):
                continue

            # Make sure this pathname will actually be able to be included
            # in the blueprint.  This is a bit of a cop-out since the file
            # could be important but at least it's not a crashing bug.
            try:
                pathname = unicode(pathname)
            except UnicodeDecodeError:
                logging.warning('{0} not UTF-8 - skipping it'.
                                format(repr(pathname)[1:-1]))
                continue

            # Ignore ignored files and files that share their ctime with other
            # files in the directory.  This is a very strong indication that
            # the file is original to the system and should be ignored.
            if ignored \
            or 1 < ctimes[s.st_ctime] and r.ignore_file(pathname, True):
                continue

            # Check for a Mustache template and an optional shell script
            # that templatize this file.
            try:
                template = open(
                    '{0}.blueprint-template.mustache'.format(pathname)).read()
            except IOError:
                template = None
            try:
                data = open(
                    '{0}.blueprint-template.sh'.format(pathname)).read()
            except IOError:
                data = None

            # The content is used even for symbolic links to determine whether
            # it has changed from the packaged version.
            try:
                content = open(pathname).read()
            except IOError:
                #logging.warning('{0} not readable'.format(pathname))
                continue

            # Ignore files that are unchanged from their packaged version.
            if _unchanged(pathname, content, r):
                continue

            # Resolve the rest of the file's metadata from the
            # `/etc/passwd` and `/etc/group` databases.
            try:
                pw = pwd.getpwuid(s.st_uid)
                owner = pw.pw_name
            except KeyError:
                owner = s.st_uid
            try:
                gr = grp.getgrgid(s.st_gid)
                group = gr.gr_name
            except KeyError:
                group = s.st_gid
            mode = '{0:o}'.format(s.st_mode)

            # A symbolic link's content is the link target.
            if stat.S_ISLNK(s.st_mode):
                content = os.readlink(pathname)

                # Ignore symbolic links providing backwards compatibility
                # between SystemV init and Upstart.
                if '/lib/init/upstart-job' == content:
                    continue

                # Ignore symbolic links into the Debian alternatives system.
                # These are almost certainly managed by packages.
                if content.startswith('/etc/alternatives/'):
                    continue

                b.add_file(pathname,
                           content=content,
                           encoding='plain',
                           group=group,
                           mode=mode,
                           owner=owner)

            # A regular file is stored as plain text only if it is valid
            # UTF-8, which is required for JSON serialization.
            else:
                kwargs = dict(group=group,
                              mode=mode,
                              owner=owner)
                try:
                    if template:
                        if data:
                            kwargs['data'] = data.decode('utf_8')
                        kwargs['template'] = template.decode('utf_8')
                    else:
                        kwargs['content'] = content.decode('utf_8')
                    kwargs['encoding'] = 'plain'
                except UnicodeDecodeError:
                    if template:
                        if data:
                            kwargs['data'] = base64.b64encode(data)
                        kwargs['template'] = base64.b64encode(template)
                    else:
                        kwargs['content'] = base64.b64encode(content)
                    kwargs['encoding'] = 'base64'
                b.add_file(pathname, **kwargs)

            # If this file is a service init script or config , create a
            # service resource.
            try:
                manager, service = util.parse_service(pathname)
                if not r.ignore_service(manager, service):
                    b.add_service(manager, service)
                    b.add_service_package(manager,
                                          service,
                                          'apt',
                                          *_dpkg_query_S(pathname))
                    b.add_service_package(manager,
                                          service,
                                          'yum',
                                          *_rpm_qf(pathname))
            except ValueError:
                pass


def _dpkg_query_S(pathname):
    """
    Return a list of package names that contain `pathname` or `[]`.  This
    really can be a list thanks to `dpkg-divert`(1).
    """

    # Cache the pathname-to-package mapping.
    if not hasattr(_dpkg_query_S, '_cache'):
        _dpkg_query_S._cache = defaultdict(set)
        cache_ref = _dpkg_query_S._cache
        for listname in glob.iglob('/var/lib/dpkg/info/*.list'):
            package = os.path.splitext(os.path.basename(listname))[0]
            for line in open(listname):
                cache_ref[line.rstrip()].add(package)

    # Return the list of packages that contain this file, if any.
    if pathname in _dpkg_query_S._cache:
        return list(_dpkg_query_S._cache[pathname])

    # If `pathname` isn't in a package but is a symbolic link, see if the
    # symbolic link is in a package.  `postinst` programs commonly display
    # this pattern.
    try:
        return _dpkg_query_S(os.readlink(pathname))
    except OSError:
        pass

    return []


def _dpkg_md5sum(package, pathname):
    """
    Find the MD5 sum of the packaged version of pathname or `None` if the
    `pathname` does not come from a Debian package.
    """

    # Cache any MD5 sums stored in the status file.  These are typically
    # conffiles and the like.
    if not hasattr(_dpkg_md5sum, '_status_cache'):
        _dpkg_md5sum._status_cache = {}
        cache_ref = _dpkg_md5sum._status_cache
        try:
            pattern = re.compile(r'^ (\S+) ([0-9a-f]{32})')
            for line in open('/var/lib/dpkg/status'):
                match = pattern.match(line)
                if not match:
                    continue
                cache_ref[match.group(1)] = match.group(2)
        except IOError:
            pass

    # Return this file's MD5 sum, if it can be found.
    try:
        return _dpkg_md5sum._status_cache[pathname]
    except KeyError:
        pass

    # Cache the MD5 sums for files in this package.
    if not hasattr(_dpkg_md5sum, '_cache'):
        _dpkg_md5sum._cache = defaultdict(dict)
    if package not in _dpkg_md5sum._cache:
        cache_ref = _dpkg_md5sum._cache[package]
        try:
            for line in open('/var/lib/dpkg/info/{0}.md5sums'.format(package)):
                md5sum, rel_pathname = line.split(None, 1)
                cache_ref['/{0}'.format(rel_pathname.rstrip())] = md5sum
        except IOError:
            pass

    # Return this file's MD5 sum, if it can be found.
    try:
        return _dpkg_md5sum._cache[package][pathname]
    except KeyError:
        pass

    return None


def _rpm_qf(pathname):
    """
    Return a list of package names that contain `pathname` or `[]`.  RPM
    might not actually support a single pathname being claimed by more
    than one package but `dpkg` does so the interface is maintained.
    """
    try:
        p = subprocess.Popen(['rpm', '--qf=%{NAME}', '-qf', pathname],
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except OSError:
        return []
    stdout, stderr = p.communicate()
    if 0 != p.returncode:
        return []
    return [stdout]


def _rpm_md5sum(pathname):
    """
    Find the MD5 sum of the packaged version of pathname or `None` if the
    `pathname` does not come from an RPM.
    """

    if not hasattr(_rpm_md5sum, '_cache'):
        _rpm_md5sum._cache = {}
        symlinks = []
        try:
            p = subprocess.Popen(['rpm', '-qa', '--dump'],
                                 close_fds=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            pattern = re.compile(r'^(/etc/\S+) \d+ \d+ ([0-9a-f]+) ' # No ,
                                  '(0\d+) \S+ \S+ \d \d \d (\S+)$')
            for line in p.stdout:
                match = pattern.match(line)
                if match is None:
                    continue
                if '0120777' == match.group(3):
                    symlinks.append((match.group(1), match.group(4)))
                else:
                    _rpm_md5sum._cache[match.group(1)] = match.group(2)

            # Find the MD5 sum of the targets of any symbolic links, even
            # if the target is outside of /etc.
            pattern = re.compile(r'^(/\S+) \d+ \d+ ([0-9a-f]+) ' # No ,
                                  '(0\d+) \S+ \S+ \d \d \d (\S+)$')
            for pathname, target in symlinks:
                if '/' != target[0]:
                    target = os.path.normpath(os.path.join(
                        os.path.dirname(pathname), target))
                if target in _rpm_md5sum._cache:
                    _rpm_md5sum._cache[pathname] = _rpm_md5sum._cache[target]
                else:
                    p = subprocess.Popen(['rpm', '-qf', '--dump', target],
                                         close_fds=True,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                    for line in p.stdout:
                        match = pattern.match(line)
                        if match is not None and target == match.group(1):
                            _rpm_md5sum._cache[pathname] = match.group(2)

        except OSError:
            pass

    return _rpm_md5sum._cache.get(pathname, None)

def _unchanged(pathname, content, r):
    """
    Return `True` if a file is unchanged from its packaged version.
    """

    # Ignore files that are from the `base-files` package (which
    # doesn't include MD5 sums for every file for some reason).
    apt_packages = _dpkg_query_S(pathname)
    if 'base-files' in apt_packages:
        return True

    # Ignore files that are unchanged from their packaged version,
    # or match in MD5SUMS.
    md5sums = MD5SUMS.get(pathname, [])
    md5sums.extend([_dpkg_md5sum(package, pathname)
                    for package in apt_packages])
    md5sum = _rpm_md5sum(pathname)
    if md5sum is not None:
        md5sums.append(md5sum)
    if (hashlib.md5(content).hexdigest() in md5sums \
        or 64 in [len(md5sum or '') for md5sum in md5sums] \
           and hashlib.sha256(content).hexdigest() in md5sums) \
       and r.ignore_file(pathname, True):
        return True

    return False
