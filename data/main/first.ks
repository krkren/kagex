@call storage="macro.ks"



; Specification of selection placement area

[selopt normal=select_normal over=select_over left=510 top=152 width=900 height=632 size=36 bold=true edge=true edgecolor=0x010062]



[iscript]



// Flag to mark everything as seen XXX Delete this eventually!!!

//tf.allseen = true;



// sf.clear (Extras on the title screen) is set once every demo has been played to the end:

// [demodone] in macro.ks



// Version

sf.software_version = "0.10.0";



// Maker

sf.software_maker = "krkren";



// Software Title

sf.software_title = "KAGEX Sample";



// Year

sf.software_year = "2026";



// Load target page

sf.loadpage = 1 if sf.loadpage === void;



/**

 * Environment initialization process

 */

function initialEnvironment()

{

    kag.noeffect     = false;

    kag.textspeed    = kag.chSpeeds.normal / (kag.chSpeeds.slow / 10);

    kag.autospeed    = kag.autoModePageWaits.medium / (kag.autoModePageWaits.slow / 10);

    kag.allskip      = false;

    kag.bgmvolume    = 80;

    kag.sevolume     = 100;

    kag.voicevolume  = 100;

    kag.setVoiceOn('voice0', true);

    kag.setVoiceOn('voice1', true);

    kag.setVoiceOn('voice2', true);

    kag.setVoiceOn('voice3', true);

    kag.setVoiceOn('voice4', true);

    kag.setVoiceOn('voice5', true);

}



// Initialize environment on first startup

if (sf.first_start != 'comp') {

    initialEnvironment();

    sf.first_start = 'comp';

}



[endscript]



[call storage="logo.ks" target="*logo"]

[jump storage=title.ks]