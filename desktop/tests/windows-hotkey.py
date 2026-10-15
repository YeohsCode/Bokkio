import ctypes,sys,time
u=ctypes.windll.user32
vk={'P':80,'R':82,'F12':123}[sys.argv[1]]
for k in [17,16,vk]:u.keybd_event(k,0,0,0)
time.sleep(.08)
for k in [vk,16,17]:u.keybd_event(k,0,2,0)
