import subprocess

cmd = ['./kindlegen.exe', '-c2', '-verbose', '-dont_append_source', 'epub/[河本ほむら×尚村透] 賭ケグルイ 第10巻.epub']
p = subprocess.Popen(cmd)
# for line in p.stdout:
#     print(line)
p.wait()
