"""Visible installer activity and measured progress; no guessed percentages."""
import os
import sys
import threading


class Progress:
    def __init__(self,label,stream=None,interval=5):
        self.label=label;self.stream=stream or sys.stderr;self.interval=interval
        self.stop=threading.Event();self.lock=threading.Lock();self.last=-1
        self.colour=self.stream.isatty() and 'NO_COLOR' not in os.environ

    def write(self,text):
        with self.lock:
            self.stream.write(text+'\n');self.stream.flush()

    def __enter__(self):
        self.write(self.label+'…')
        def activity():
            while not self.stop.wait(self.interval):self.write(self.label+'… still working')
        self.thread=threading.Thread(target=activity,name='jarvis-installer-progress',daemon=True)
        self.thread.start()
        return self

    def fraction(self,current,total):
        if total<=0:return
        percentage=min(100,max(0,int(current*100/total)))
        bucket=percentage//5
        with self.lock:
            if bucket<=self.last:return
            self.last=bucket
            bar='['+'='*(percentage//5)+' '*(20-percentage//5)+']'
            if self.colour:bar='\033[32m'+bar+'\033[0m'
            self.stream.write(f'{self.label}: {bar} {percentage}%\n');self.stream.flush()

    def __exit__(self,kind,error,traceback):
        self.stop.set();self.thread.join(timeout=1)
        self.write(self.label+(': complete' if kind is None else ': failed'))
