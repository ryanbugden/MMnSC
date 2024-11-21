

# MMnSC
**MMnSC** (rename not fully implemented yet) is a fork of MM2SpaceCenter. The main difference is that the UI is not embedded into Space Center, rather than being a separate window. There have been other changes, detailed below.

![](_images/new_popover.png)
##### UI revamp:

* implemented UI as a button in SC with a popover pref window 
* removed status bar. it was unnecessary, because the prefs are no longer always visible, and the status is spelled out in Space Center itself
* rebuilt the UI with [ezui](https://typesupply.github.io/ezui/overview.html)

##### Code rewrite:

* refactored most of the code, for performance, readability, extensibility

##### New features:

* remember user’s settings automatically
* apply Space Center’s Show Kerning upon use
* open-close and automatic spacing strings are now compatible with unencoded suffixed glyphs.
* you may have multiple Space Centers open at once, with MM2SC affecting all of them. this way, you can kern while looking at different sizes/line-heights/tracking/alignment simultaneously.

##### Future considerations:

* observer activates when the Space Center opens. checking the on-off checkbox doesn't toggle the observer itself, so it may be a bit expensive... ideally there will be MetricsMachine support via [Subscriber](https://robofont.com/documentation/reference/api/mojo/mojo-subscriber/?highlight=mojo.subscriber). all said, it doesn’t feel slower than before.
* other thoughts are either commented in the code, or filed as [issues](https://github.com/cjdunn/MM2SpaceCenter/issues).


## Original Description

This extension generates a list of words in RoboFont’s Space Center based on the current pair you’re kerning in the [MetricsMachine](https://extensionstore.robofont.com/extensions/metricsMachine/) extension by Tal Leming.

The wonderful [word-o-mat] extension by Nina Stössinger was a major influence, and this would most certainly not exist if Nina’s word-o-mat hadn’t come first. And thanks to Stephen Nixon for asking about something like this, which encouraged me to share this. I would love to see this extension evolve to have nice menus and an interface as powerful as word-o-mat someday.