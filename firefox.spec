# Use system nss/nspr?
%define system_nss        1

# Separated plugins are supported on x86(64) only
%ifarch %{ix86} x86_64
%define separated_plugins 1
%else
%define separated_plugins 0
%endif

# Build as a debug package?
%define debug_build       0

%define default_bookmarks_file %{_datadir}/bookmarks/default-bookmarks.html
%define firefox_app_id \{ec8030f7-c20a-464f-9b0e-13a3a9e97384\}

%global xulrunner_version      25.0
%global xulrunner_version_max  25.1
%global xulrunner_release      2
%global alpha_version          0
%global beta_version           0
%global rc_version             0

%global mozappdir     %{_libdir}/%{name}
%global langpackdir   %{mozappdir}/langpacks
%global tarballdir    mozilla-release

%define official_branding       1
%define build_langpacks         1
%ifarch %{ix86} x86_64
%define enable_mozilla_crashreporter       1
%else
%define enable_mozilla_crashreporter       0
%endif

%if %{alpha_version} > 0
%global pre_version a%{alpha_version}
%global pre_name    alpha%{alpha_version}
%global tarballdir  mozilla-alpha
%endif
%if %{beta_version} > 0
%global pre_version b%{beta_version}
%global pre_name    beta%{beta_version}
%global tarballdir  mozilla-beta
%endif
%if %{rc_version} > 0
%global pre_version rc%{rc_version}
%global pre_name    rc%{rc_version}
%global tarballdir  mozilla-release
%endif
%if %{defined pre_version}
%global xulrunner_verrel %{xulrunner_version}-%{xulrunner_release}
%global pre_tag .%{pre_version}
%else
%global xulrunner_verrel %{xulrunner_version}-%{xulrunner_release}
%endif

Summary:        Mozilla Firefox Web browser
Name:           firefox
Version:        26.0
Release:        1%{?pre_tag}%{?dist}
URL:            http://www.mozilla.org/projects/firefox/
License:        MPLv1.1 or GPLv2+ or LGPLv2+
Group:          Applications/Internet
Source0:        ftp://ftp.mozilla.org/pub/firefox/releases/%{version}%{?pre_version}/source/firefox-%{version}%{?pre_version}.source.tar.bz2
%if %{build_langpacks}
Source1:        firefox-langpacks-%{version}%{?pre_version}-20131209.tar.xz
%endif
Source10:       firefox-mozconfig
Source11:       firefox-mozconfig-branded
Source12:       firefox-redhat-default-prefs.js
Source20:       firefox.desktop
Source21:       firefox.sh.in
Source23:       firefox.1

#Build patches
Patch0:         firefox-install-dir.patch

# Fedora patches
Patch14:        firefox-5.0-asciidel.patch
Patch15:        firefox-15.0-enable-addons.patch
Patch16:        firefox-duckduckgo.patch

# Upstream patches

%if %{official_branding}
# Required by Mozilla Corporation


%else
# Not yet approved by Mozillla Corporation

%endif

# ---------------------------------------------------

BuildRequires:  desktop-file-utils
BuildRequires:  system-bookmarks
BuildRequires:  xulrunner-devel%{?_isa} >= %{xulrunner_verrel}

Requires:       xulrunner%{?_isa} >= %{xulrunner_verrel}
Requires:       system-bookmarks
Obsoletes:      mozilla <= 37:1.7.13
Provides:       webclient
Conflicts:      xulrunner%{?_isa} > %{xulrunner_version_max}

%description
Mozilla Firefox is an open-source web browser, designed for standards
compliance, performance and portability.

#---------------------------------------------------------------------

%prep
%setup -q -c
cd %{tarballdir}

# Build patches, can't change backup suffix from default because during build
# there is a compare of config and js/config directories and .orig suffix is 
# ignored during this compare.
%patch0 -p1

# For branding specific patches.

# Fedora patches
%patch14 -p1 -b .asciidel
%patch15 -p2 -b .addons
%patch16 -p1 -b .duckduckgo

# Upstream patches

%if %{official_branding}
# Required by Mozilla Corporation

%else
# Not yet approved by Mozilla Corporation
%endif


%{__rm} -f .mozconfig
%{__cp} %{SOURCE10} .mozconfig
%if %{official_branding}
%{__cat} %{SOURCE11} >> .mozconfig
%endif

# Set up SDK path
MOZILLA_SDK_PATH=`pkg-config --variable=sdkdir libxul`
if [ -z "$MOZILLA_SDK_PATH" ]; then
    echo "XulRunner SDK is not available!"
    exit 1
else
    echo "XulRunner SDK path: $MOZILLA_SDK_PATH"
    echo "ac_add_options --with-libxul-sdk=$MOZILLA_SDK_PATH" >> .mozconfig
fi

%if !%{?separated_plugins}
echo "ac_add_options --disable-ipc" >> .mozconfig
%endif

%ifarch %{arm}
echo "ac_add_options --disable-elf-hack" >> .mozconfig
%endif

%if %{?debug_build}
echo "ac_add_options --enable-debug" >> .mozconfig
echo "ac_add_options --disable-optimize" >> .mozconfig
%else
echo "ac_add_options --disable-debug" >> .mozconfig
echo "ac_add_options --enable-optimize" >> .mozconfig
%endif

%if %{?system_nss}
echo "ac_add_options --with-system-nspr" >> .mozconfig
echo "ac_add_options --with-system-nss" >> .mozconfig
%else
echo "ac_add_options --without-system-nspr" >> .mozconfig
echo "ac_add_options --without-system-nss" >> .mozconfig
%endif

# s390(x) fails to start with jemalloc enabled
%ifarch s390 s390x
echo "ac_add_options --disable-jemalloc" >> .mozconfig
%endif

#---------------------------------------------------------------------

%build
cd %{tarballdir}

# Mozilla builds with -Wall with exception of a few warnings which show up
# everywhere in the code; so, don't override that.
#
# Disable C++ exceptions since Mozilla code is not exception-safe
#
MOZ_OPT_FLAGS=$(echo $RPM_OPT_FLAGS | \
                     %{__sed} -e 's/-Wall//')
%if %{?debug_build}
MOZ_OPT_FLAGS=$(echo "$MOZ_OPT_FLAGS" | %{__sed} -e 's/-O2//')
%endif
%ifarch s390
MOZ_OPT_FLAGS=$(echo "$MOZ_OPT_FLAGS" | %{__sed} -e 's/-g/-g1/')
%endif
%ifarch s390 %{arm} ppc
MOZ_LINK_FLAGS="-Wl,--no-keep-memory -Wl,--reduce-memory-overheads"
%endif
export CFLAGS=$MOZ_OPT_FLAGS
export CXXFLAGS=$MOZ_OPT_FLAGS

export PREFIX='%{_prefix}'
export LIBDIR='%{_libdir}'

MOZ_SMP_FLAGS=-j1
# On x86 architectures, Mozilla can build up to 4 jobs at once in parallel,
# however builds tend to fail on other arches when building in parallel.
%ifarch %{ix86} x86_64
[ -z "$RPM_BUILD_NCPUS" ] && \
     RPM_BUILD_NCPUS="`/usr/bin/getconf _NPROCESSORS_ONLN`"
[ "$RPM_BUILD_NCPUS" -ge 2 ] && MOZ_SMP_FLAGS=-j2
[ "$RPM_BUILD_NCPUS" -ge 4 ] && MOZ_SMP_FLAGS=-j4
%endif

export LDFLAGS="-Wl,-rpath,%{mozappdir}"
make -f client.mk build STRIP="/bin/true" MOZ_MAKE_FLAGS="$MOZ_SMP_FLAGS"

#---------------------------------------------------------------------

%install
cd %{tarballdir}

# set up our prefs and add it to the package manifest file, so it gets pulled in
# to omni.jar which gets created during make install
%{__cp} %{SOURCE12} dist/bin/browser/defaults/preferences/all-redhat.js
# This sed call "replaces" firefox.js with all-redhat.js, newline, and itself (&)
# having the net effect of prepending all-redhat.js above firefox.js
%{__sed} -i -e\
    's|@BINPATH@/browser/@PREF_DIR@/firefox.js|@BINPATH@/browser/@PREF_DIR@/all-redhat.js\n&|' \
    browser/installer/package-manifest.in

# set up our default bookmarks
%{__cp} -p %{default_bookmarks_file} dist/bin/browser/defaults/profile/bookmarks.html

# Make sure locale works for langpacks
%{__cat} > dist/bin/browser/defaults/preferences/firefox-l10n.js << EOF
pref("general.useragent.locale", "chrome://global/locale/intl.properties");
EOF

DESTDIR=$RPM_BUILD_ROOT make install

%{__mkdir_p} $RPM_BUILD_ROOT{%{_libdir},%{_bindir},%{_datadir}/applications}

%if 0%{?fedora} <= 16
desktop-file-install --vendor mozilla --dir $RPM_BUILD_ROOT%{_datadir}/applications %{SOURCE20}
%else
desktop-file-install --dir $RPM_BUILD_ROOT%{_datadir}/applications %{SOURCE20}
%endif

# set up the firefox start script
%{__rm} -rf $RPM_BUILD_ROOT%{_bindir}/firefox
XULRUNNER_DIR=`pkg-config --variable=libdir libxul | %{__sed} -e "s,%{_libdir}/\?,,g"`
%{__cat} %{SOURCE21} | %{__sed} -e "s,XULRUNNER_DIRECTORY,$XULRUNNER_DIR,g" > \
  $RPM_BUILD_ROOT%{_bindir}/firefox
%{__chmod} 755 $RPM_BUILD_ROOT%{_bindir}/firefox

# Link with xulrunner 
ln -s `pkg-config --variable=libdir libxul` $RPM_BUILD_ROOT/%{mozappdir}/xulrunner

%{__install} -p -D -m 644 %{SOURCE23} $RPM_BUILD_ROOT%{_mandir}/man1/firefox.1

%{__rm} -f $RPM_BUILD_ROOT/%{mozappdir}/firefox-config
%{__rm} -f $RPM_BUILD_ROOT/%{mozappdir}/update-settings.ini

for s in 16 22 24 32 48 256; do
    %{__mkdir_p} $RPM_BUILD_ROOT%{_datadir}/icons/hicolor/${s}x${s}/apps
    %{__cp} -p browser/branding/official/default${s}.png \
               $RPM_BUILD_ROOT%{_datadir}/icons/hicolor/${s}x${s}/apps/firefox.png
done

echo > ../%{name}.lang
%if %{build_langpacks}
# Extract langpacks, make any mods needed, repack the langpack, and install it.
%{__mkdir_p} $RPM_BUILD_ROOT%{langpackdir}
%{__tar} xf %{SOURCE1}
for langpack in `ls firefox-langpacks/*.xpi`; do
  language=`basename $langpack .xpi`
  extensionID=langpack-$language@firefox.mozilla.org
  %{__mkdir_p} $extensionID
  unzip -qq $langpack -d $extensionID
  find $extensionID -type f | xargs chmod 644

  cd $extensionID
  zip -qq -r9mX ../${extensionID}.xpi *
  cd -

  %{__install} -m 644 ${extensionID}.xpi $RPM_BUILD_ROOT%{langpackdir}
  language=`echo $language | sed -e 's/-/_/g'`
  echo "%%lang($language) %{langpackdir}/${extensionID}.xpi" >> ../%{name}.lang
done
%{__rm} -rf firefox-langpacks
%endif # build_langpacks

# Install langpack workaround (see #707100, #821169)
function create_default_langpack() {
language_long=$1
language_short=$2
cd $RPM_BUILD_ROOT%{langpackdir}
ln -s langpack-$language_long@firefox.mozilla.org.xpi langpack-$language_short@firefox.mozilla.org.xpi
cd -
echo "%%lang($language_short) %{langpackdir}/langpack-$language_short@firefox.mozilla.org.xpi" >> ../%{name}.lang
}

# Table of fallbacks for each language
# please file a bug at bugzilla.redhat.com if the assignment is incorrect
create_default_langpack "bn-IN" "bn"
create_default_langpack "es-AR" "es"
create_default_langpack "fy-NL" "fy"
create_default_langpack "ga-IE" "ga"
create_default_langpack "gu-IN" "gu"
create_default_langpack "hi-IN" "hi"
create_default_langpack "hy-AM" "hy"
create_default_langpack "nb-NO" "nb"
create_default_langpack "nn-NO" "nn"
create_default_langpack "pa-IN" "pa"
create_default_langpack "pt-PT" "pt"
create_default_langpack "sv-SE" "sv"
create_default_langpack "zh-TW" "zh"

# Keep compatibility with the old preference location 
# on Fedora 18 and earlier
%if 0%{?fedora} < 19
%{__mkdir_p} $RPM_BUILD_ROOT/%{mozappdir}/defaults/preferences
%{__mkdir_p} $RPM_BUILD_ROOT/%{mozappdir}/browser/defaults
ln -s %{mozappdir}/defaults/preferences $RPM_BUILD_ROOT/%{mozappdir}/browser/defaults/preferences
%else
%{__mkdir_p} $RPM_BUILD_ROOT/%{mozappdir}/browser/defaults/preferences
%endif

# System extensions
%{__mkdir_p} $RPM_BUILD_ROOT%{_datadir}/mozilla/extensions/%{firefox_app_id}
%{__mkdir_p} $RPM_BUILD_ROOT%{_libdir}/mozilla/extensions/%{firefox_app_id}

# Copy over the LICENSE
%{__install} -p -c -m 644 LICENSE $RPM_BUILD_ROOT/%{mozappdir}

# Enable crash reporter for Firefox application
%if %{enable_mozilla_crashreporter}
sed -i -e "s/\[Crash Reporter\]/[Crash Reporter]\nEnabled=1/" $RPM_BUILD_ROOT/%{mozappdir}/application.ini
%endif

#---------------------------------------------------------------------

# Moves defaults/preferences to browser/defaults/preferences in Fedora 19+
%if 0%{?fedora} >= 19
%pretrans -p <lua>
require 'posix'
require 'os'
if (posix.stat("%{mozappdir}/browser/defaults/preferences", "type") == "link") then
  posix.unlink("%{mozappdir}/browser/defaults/preferences")
  posix.mkdir("%{mozappdir}/browser/defaults/preferences")
  if (posix.stat("%{mozappdir}/defaults/preferences", "type") == "directory") then
    for i,filename in pairs(posix.dir("%{mozappdir}/defaults/preferences")) do 
      os.rename("%{mozappdir}/defaults/preferences/"..filename, "%{mozappdir}/browser/defaults/preferences/"..filename)
    end
    f = io.open("%{mozappdir}/defaults/preferences/README","w")
    if f then
      f:write("Content of this directory has been moved to %{mozappdir}/browser/defaults/preferences.")
      f:close()
    end
  end
end
%endif

%preun
# is it a final removal?
if [ $1 -eq 0 ]; then
  %{__rm} -rf %{mozappdir}/components
  %{__rm} -rf %{mozappdir}/extensions
  %{__rm} -rf %{mozappdir}/plugins
  %{__rm} -rf %{langpackdir}
fi

%post
update-desktop-database &> /dev/null || :
touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :

%postun
update-desktop-database &> /dev/null || :
if [ $1 -eq 0 ] ; then
    touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi

%posttrans
gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%files -f %{name}.lang
%defattr(-,root,root,-)
%{_bindir}/firefox
%{mozappdir}/firefox
%{mozappdir}/firefox-bin
%doc %{_mandir}/man1/*
%dir %{_datadir}/mozilla/extensions/%{firefox_app_id}
%dir %{_libdir}/mozilla/extensions/%{firefox_app_id}
%{_datadir}/applications/*.desktop
%dir %{mozappdir}
%doc %{mozappdir}/LICENSE
%{mozappdir}/browser/chrome
%{mozappdir}/browser/chrome.manifest
%dir %{mozappdir}/browser/components
%{mozappdir}/browser/components/*.so
%{mozappdir}/browser/components/components.manifest
%if 0%{?fedora} < 19
%dir %{mozappdir}/defaults/preferences
%{mozappdir}/browser/defaults/preferences
%else
%dir %{mozappdir}/browser/defaults/preferences
%endif
%attr(644, root, root) %{mozappdir}/browser/blocklist.xml
%dir %{mozappdir}/browser/extensions
%{mozappdir}/browser/extensions/{972ce4c6-7e08-4474-a285-3208198ce6fd}
%if %{build_langpacks}
%dir %{langpackdir}
%endif
%{mozappdir}/browser/omni.ja
%{mozappdir}/browser/icons
%{mozappdir}/browser/searchplugins
%{mozappdir}/run-mozilla.sh
%{mozappdir}/application.ini
%exclude %{mozappdir}/removed-files
%{_datadir}/icons/hicolor/16x16/apps/firefox.png
%{_datadir}/icons/hicolor/22x22/apps/firefox.png
%{_datadir}/icons/hicolor/24x24/apps/firefox.png
%{_datadir}/icons/hicolor/256x256/apps/firefox.png
%{_datadir}/icons/hicolor/32x32/apps/firefox.png
%{_datadir}/icons/hicolor/48x48/apps/firefox.png
%{mozappdir}/xulrunner
%{mozappdir}/webapprt-stub
%dir %{mozappdir}/webapprt
%{mozappdir}/webapprt/omni.ja
%{mozappdir}/webapprt/webapprt.ini
%if %{enable_mozilla_crashreporter}
%{mozappdir}/browser/crashreporter-override.ini
%endif

#---------------------------------------------------------------------

%changelog
* Mon Dec 9 2013 Martin Stransky <stransky@redhat.com> - 26.0-1
- Update to 26.0 Build 2

* Wed Oct 30 2013 Martin Stransky <stransky@redhat.com> - 25.0-3
- Update to 25.0 Build 3

* Thu Oct 24 2013 Martin Stransky <stransky@redhat.com> - 25.0-2
- Fixed xulrunner dependency

* Thu Oct 24 2013 Martin Stransky <stransky@redhat.com> - 25.0-1
- Update to 25.0 Build 2

* Thu Oct 17 2013 Martin Stransky <stransky@redhat.com> - 24.0-2
- Fixed rhbz#1005611 - BEAST workaround not enabled in Firefox

* Fri Sep 13 2013 Martin Stransky <stransky@redhat.com> - 24.0-1
- Update to 24.0

* Tue Sep  3 2013 Jan Horak <jhorak@redhat.com> - 23.0.1-5
- Fixing rhbz#1003691

* Fri Aug 30 2013 Martin Stransky <stransky@redhat.com> - 23.0.1-3
- Spec tweak (rhbz#991493)

* Fri Aug 30 2013 Jan Horak <jhorak@redhat.com> - 23.0.1-2
- Homepage moved to pref file
- Fixed migration from F18 -> F19 (rhbz#976420)

* Mon Aug 19 2013 Jan Horak <jhorak@redhat.com> - 23.0.1-1
- Update to 23.0.1

* Mon Aug 5 2013 Martin Stransky <stransky@redhat.com> - 23.0-1
- Updated to latest upstream (23.0 Build 2)

* Thu Jul 25 2013 Martin Stransky <stransky@redhat.com> - 22.0-3
- Fixed rhbz#988363 - firefox-redhat-default-prefs.js is not used

* Fri Jun 28 2013 Jan Horak <jhorak@redhat.com> - 22.0-2
- Fixed crashreporter for third arch

* Fri Jun 21 2013 Martin Stransky <stransky@redhat.com> - 22.0-1
- Updated to latest upstream (22.0)

* Thu Jun 13 2013 Jan Horak <jhorak@redhat.com> - 21.0-5
- Enable Mozilla crash report tool

* Thu May 23 2013 Jan Horak <jhorak@redhat.com> - 21.0-4
- Do not override user defined TMPDIR variable

* Thu May 16 2013 Martin Stransky <stransky@redhat.com> - 21.0-3
- Fixed extension compatibility dialog (rhbz#963422)

* Wed May 15 2013 Martin Stransky <stransky@redhat.com> - 21.0-2
- Keep compatibility with old preference dir

* Tue May 14 2013 Martin Stransky <stransky@redhat.com> - 21.0-1
- Updated to latest upstream (21.0)

* Thu May 9 2013 Martin Stransky <stransky@redhat.com> - 20.0-5
- Removed firstrun page (rhbz#864793)
- Made zip/unzip quiet in langpacks processing

* Thu Apr 18 2013 Martin Stransky <stransky@redhat.com> - 20.0-4
- Updated xulrunner check

* Thu Apr 18 2013 Martin Stransky <stransky@redhat.com> - 20.0-3
- Added a workaround for rhbz#907424 - textarea redrawn wrongly 
  during edit

* Thu Apr 18 2013 Jan Horak <jhorak@redhat.com> - 20.0-2
- Updated manual page

* Mon Apr 1 2013 Martin Stransky <stransky@redhat.com> - 20.0-1
- Updated to 20.0

* Mon Mar 18 2013 Martin Stransky <stransky@redhat.com> - 19.0.2-2
- Added fix for mozbz#239254 - local cache dir

* Mon Mar 11 2013 Jan Horak <jhorak@redhat.com> - 19.0.2-1
- Update to 19.0.2

* Tue Feb 19 2013 Jan Horak <jhorak@redhat.com> - 19.0-1
- Update to 19.0

* Wed Feb  6 2013 Jan Horak <jhorak@redhat.com> - 18.0.2-1
- Update to 18.0.2

* Fri Jan 25 2013 Jan Horak <jhorak@redhat.com> - 18.0.1-1
- Update to 18.0.1

* Wed Jan 9 2013 Martin Stransky <stransky@redhat.com> - 18.0-1
- Update to 18.0

* Tue Dec 18 2012 Martin Stransky <stransky@redhat.com> - 17.0.1-2
- Fix bug 878831 - Please enable gfx.color_management.enablev4=true

* Thu Nov 29 2012 Jan Horak <jhorak@redhat.com> - 17.0.1-1
- Update to 17.0.1

* Mon Nov 19 2012 Martin Stransky <stransky@redhat.com> - 17.0-1
- Update to 17.0

* Thu Nov 15 2012 Martin Stransky <stransky@redhat.com> - 17.0-0.1b6
- Update to 17.0 Beta 6

* Wed Nov  7 2012 Jan Horak <jhorak@redhat.com> - 16.0.2-4
- Added duckduckgo.com search engine

* Thu Nov  1 2012 Jan Horak <jhorak@redhat.com> - 16.0.2-3
- Added keywords to desktop file (871900)

* Tue Oct 30 2012 Martin Stransky <stransky@redhat.com> - 16.0.2-2
- Updated man page (#800234)

* Fri Oct 26 2012 Jan Horak <jhorak@redhat.com> - 16.0.2-1
- Update to 16.0.2

* Thu Oct 11 2012 Martin Stransky <stransky@redhat.com> - 16.0.1-1
- Update to 16.0.1

* Thu Oct 11 2012 Martin Stransky <stransky@redhat.com> - 16.0.1-1
- Update to 16.0.1

* Mon Oct  8 2012 Jan Horak <jhorak@redhat.com> - 16.0-1
- Update to 16.0
- Use /var/tmp instead of /tmp (rhbz#860814)

* Tue Sep 11 2012 Jan Horak <jhorak@redhat.com> - 15.0.1-1
- Update to 15.0.1

* Tue Aug 28 2012 Martin Stransky <stransky@redhat.com> - 15.0-2
- Added fix for rhbz#851722 - conflict with incompatible xulrunner

* Mon Aug 27 2012 Martin Stransky <stransky@redhat.com> - 15.0-1
- Update to 15.0

* Wed Aug 22 2012 Dan Horák <dan[at]danny.cz> - 14.0.1-3
- add fix for secondary arches from xulrunner

* Wed Aug 1 2012 Martin Stransky <stransky@redhat.com> - 14.0.1-2
- removed StartupWMClass (rhbz#844860)

* Mon Jul 16 2012 Martin Stransky <stransky@redhat.com> - 14.0.1-1
- Update to 14.0.1

* Tue Jul 10 2012 Martin Stransky <stransky@redhat.com> - 13.0.1-2
- Fixed rhbz#707100, rhbz#821169

* Sat Jun 16 2012 Jan Horak <jhorak@redhat.com> - 13.0.1-1
- Update to 13.0.1

* Tue Jun 5 2012 Martin Stransky <stransky@redhat.com> - 13.0-1
- Update to 13.0

* Tue Apr 24 2012 Martin Stransky <stransky@redhat.com> - 12.0-1
- Update to 12.0

* Thu Mar 15 2012 Martin Stransky <stransky@redhat.com> - 11.0-2
- Switched dependency to xulrunner (rhbz#803471)

* Tue Mar 13 2012 Martin Stransky <stransky@redhat.com> - 11.0-1
- Update to 11.0
- Fixed rhbz#800622 - make default home page of fedoraproject.org conditional
- Fixed rhbz#801796 - enable debug build by some simple way

* Mon Feb 27 2012 Peter Robinson <pbrobinson@fedoraproject.org> - 10.0.1-2
- Add ARM config options to fix compile

* Thu Feb  9 2012 Jan Horak <jhorak@redhat.com> - 10.0.1-1
- Update to 10.0.1

* Fri Feb  3 2012 Jan Horak <jhorak@redhat.com> - 10.0-2
- Fixed rhbz#786983

* Tue Jan 31 2012 Jan Horak <jhorak@redhat.com> - 10.0-1
- Update to 10.0

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 9.0.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Fri Dec 23 2011 Jan Horak <jhorak@redhat.com> - 9.0.1-1
- Update to 9.0.1

* Wed Dec 21 2011 Jan Horak <jhorak@redhat.com> - 9.0-3
- Update to 9.0

* Thu Dec 15 2011 Jan Horak <jhorak@redhat.com> - 9.0-1.beta5
- Update to 9.0 Beta 5

* Tue Nov 15 2011 Martin Stransky <stransky@redhat.com> - 8.0-3
- Disabled addon check UI (#753551)

* Tue Nov 15 2011 Martin Stransky <stransky@redhat.com> - 8.0-2
- Temporary workaround for langpacks (#753551)

* Tue Nov  8 2011 Jan Horak <jhorak@redhat.com> - 8.0-1
- Update to 8.0

* Mon Oct 24 2011 Martin Stransky <stransky@redhat.com> - 7.0.1-3
- reverted the desktop file name for Fedora15 & 16

* Mon Oct 24 2011 Martin Stransky <stransky@redhat.com> - 7.0.1-2
- renamed mozilla-firefox.desktop to firefox.desktop (#736558)
- nspluginwrapper is not run in plugin-container (#747981)

* Fri Sep 30 2011 Jan Horak <jhorak@redhat.com> - 7.0.1-1
- Update to 7.0.1

* Tue Sep 27 2011 Jan Horak <jhorak@redhat.com> - 7.0
- Update to 7.0

* Tue Sep  6 2011 Jan Horak <jhorak@redhat.com> - 6.0.2-1
- Update to 6.0.2

* Tue Aug 16 2011 Martin Stransky <stransky@redhat.com> - 6.0-1
- Update to 6.0

* Fri Jun 24 2011 Bill Nottingham <notting@redhat.com> - 5.0-2
- Fix an issue with a stray glyph in the window title

* Tue Jun 21 2011 Martin Stransky <stransky@redhat.com> - 5.0-1
- Update to 5.0

* Tue May 10 2011 Martin Stransky <stransky@redhat.com> - 4.0.1-2
- Fixed rhbz#676183 - "firefox -g" is broken

* Thu Apr 28 2011 Christopher Aillon <caillon@redhat.com> - 4.0.1-1
- Update to 4.0.1

* Thu Apr 21 2011 Christopher Aillon <caillon@redhat.com> - 4.0-4
- Spec file cleanups

* Mon Apr  4 2011 Christopher Aillon <caillon@redhat.com> - 4.0-3
- Updates for NetworkManager 0.9
- Updates for GNOME 3

* Tue Mar 22 2011 Christopher Aillon <caillon@redhat.com> - 4.0-2
- Rebuild

* Tue Mar 22 2011 Christopher Aillon <caillon@redhat.com> - 4.0-1
- Firefox 4

* Fri Mar 18 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.21
- Firefox 4.0 RC 2

* Thu Mar 17 2011 Jan Horak <jhorak@redhat.com> - 4.0-0.20
- Rebuild against xulrunner with disabled gnomevfs and enabled gio

* Wed Mar  9 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.19
- Firefox 4.0 RC 1

* Sat Feb 26 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.18b12
- Switch to using the omni chrome file format

* Fri Feb 25 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.17b12
- Firefox 4.0 Beta 12

* Thu Feb 10 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.16b11
- Update gecko-{libs,devel} requires

* Tue Feb 08 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.15b11
- Firefox 4.0 Beta 11

* Mon Feb 07 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.14b10
- Bring back the default browser check

* Tue Jan 25 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.13b10
- Firefox 4.0 Beta 10

* Fri Jan 14 2011 Christopher Aillon <caillon@redhat.com> - 4.0-0.12b9
- Firefox 4.0 Beta 9

* Thu Jan 6 2011 Dan Horák <dan[at]danny.cz> - 4.0-0.11b8
- disable ipc on non-x86 arches to match xulrunner

* Thu Jan 6 2011 Martin Stransky <stransky@redhat.com> - 4.0-0.10b8
- application.ini permission check fix

* Thu Jan 6 2011 Martin Stransky <stransky@redhat.com> - 4.0-0.9b8
- Fixed rhbz#667477 - broken launch script

* Tue Jan 4 2011 Martin Stransky <stransky@redhat.com> - 4.0-0.8b8
- Fixed rhbz#664877 - Cannot read application.ini
