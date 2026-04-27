// extrans.dll has no Linux port yet; load only if plugin file exists
[iscript]
try {
	var plPath = Storages.getPlacedPath("extrans.dll");
	if (plPath != "" && Storages.isExistentStorage(plPath)) {
		Plugins.link("extrans.dll");
	}
} catch {}
[endscript]

@call storage="macro.ks"



; Specification of selection placement area

[selopt normal=select_normal over=select_over left=100 top=80 width=600 height=360]



[iscript]



// Flag to mark everything as seen XXX Delete this eventually!!!

//tf.allseen = true;



// Force clear flag ON XXX Delete this eventually!!!

sf.clear = true;



// Version

sf.software_version = "1.00";



// Maker

sf.software_maker = "Mystery";



// Software Title

sf.software_title = "Mystery Game";



// Year

sf.software_year = "2006";



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