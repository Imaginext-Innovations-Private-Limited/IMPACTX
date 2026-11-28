class MicrophoneCapture extends AudioWorkletProcessor {
 constructor(){
  super();
  this.buffer=new Float32Array(4096);
  this.used=0;
  this.stopped=false;
  this.port.onmessage=()=>{
   this.flush();
   this.stopped=true;
   this.port.postMessage('done');
  };
 }
 flush(){
  if(this.used)this.port.postMessage(this.buffer.slice(0,this.used));
  this.used=0;
 }
 process(inputs){
  if(this.stopped)return false;
  const mono=inputs[0]?.[0];
  if(mono)for(const value of mono){
   this.buffer[this.used++]=value;
   if(this.used===this.buffer.length)this.flush();
  }
  return true;
 }
}
registerProcessor('welfare-microphone',MicrophoneCapture);
