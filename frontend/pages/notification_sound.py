"""Short alert tones for newly arrived notifications only."""
from nicegui import ui


def play_alert_sound():
    ui.run_javascript("""(()=>{
      try {
        const context=new(window.AudioContext||window.webkitAudioContext)();
        const tone=(frequency,start,duration)=>{
          const oscillator=context.createOscillator(),gain=context.createGain();
          oscillator.connect(gain);gain.connect(context.destination);
          oscillator.frequency.value=frequency;
          gain.gain.setValueAtTime(.3,context.currentTime+start);
          gain.gain.exponentialRampToValueAtTime(.001,context.currentTime+start+duration);
          oscillator.start(context.currentTime+start);
          oscillator.stop(context.currentTime+start+duration+.05);
        };
        tone(880,0,.18);tone(660,.2,.18);tone(880,.4,.25);
        setTimeout(()=>context.close(),1200);
      } catch(error) {}
    })()""")
