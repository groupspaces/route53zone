#!/usr/bin/python
# Author: Gabor Vizi (@vgabor)
#
# using bind zone files for amazon route53
# (it utilizes boto and dnspython)

import sys
import dns.zone
import boto.route53.record

def sync_zonefile(conn, zone_file, alias_map_file=None, debug_file=None, comment=None):
    """Set the zone from a bind zonefile"""
    alias_map = {}
    if alias_map_file:
	for line in open(alias_map_file, 'r'):
		m = line.split()
		if len(m) >= 3 and m[0][0] != "#":
		    if m[2][-1] != ".":
			m[2] += "."
		    alias_map[m[0]] = (m[1], m[2].lower(), m[3:])
    def in_alias_map(type, ip, domain):
	if (type in ['A', 'CNAME']) and ip in alias_map:
	    if len(alias_map[ip][2]) == 0:
		return True
	    if alias_map[ip][2][0] == "!":
		return domain not in alias_map[ip][2]
	    return domain in alias_map[ip][2]
	return False

    skiptype = ("SOA", "NS")
    zonedata = {}
    zone = dns.zone.from_file(zone_file,relativize=False)
    origin = zone.origin.to_text()
    for record_type in boto.route53.record.RECORD_TYPES:
	if record_type not in skiptype:
	    records = zone.iterate_rdatas(record_type)
	    for (name, ttl, rdata) in records:
		type = unicode(record_type)
		name = name.to_unicode()
		data = unicode(rdata.to_text())
		if in_alias_map(type, data, origin[:-1]):
		    ttl = unicode(600)
		    type = "A"
		else:
		    ttl = unicode(ttl)
		key = (name, type, ttl)
		if key not in zonedata:
		    zonedata[key] = boto.route53.record.Record(name, type, ttl)
		if in_alias_map(type, data, origin[:-1]):
		    zonedata[key].set_alias(alias_map[data][0], alias_map[data][1])
		else:
		    zonedata[key].add_value(unicode(rdata.to_text()))

    hosted_zone_id = None
    for z in conn.get_all_hosted_zones().values()[0]['HostedZones']:
        if z['Name'] == origin:
            hosted_zone_id = z['Id'].replace('/hostedzone/', '')
            break
    if hosted_zone_id == None:
	print zone.origin, "is non-existing on route53:", [str(zoneinfo['Name']) for zoneinfo in conn.get_all_hosted_zones()['ListHostedZonesResponse']['HostedZones']]
	return

    current = {}
    result = conn.get_all_rrsets(hosted_zone_id);
    for record in result:
	if record.type not in skiptype:
	    record.name = record.name.decode("string_escape")
	    key = (record.name, record.type, unicode(record.ttl))
	    current[key] = record

    keys_current = set(current.iterkeys())
    keys_zonedata = set(zonedata.iterkeys())
    key_remove = keys_current - keys_zonedata
    key_add = keys_zonedata - keys_current
    for key in keys_current & keys_zonedata:
	if current[key].to_xml() != zonedata[key].to_xml():
	    key_remove.add(key), key_add.add(key)

    changeset = boto.route53.record.ResourceRecordSets(conn, hosted_zone_id, comment)
    for key in key_remove:
	changeset.changes.append(["DELETE", current[key]])
    for key in key_add:
	changeset.changes.append(["CREATE", zonedata[key]])
    if len(changeset.changes) > 0:
	result = changeset.commit()
	#result = ''
	if debug_file != None:
	    from datetime import datetime
	    f = open(debug_file, 'a')
	    f.write(' '.join([datetime.now().ctime(), zone_file, zone.origin.to_text(), hosted_zone_id, str(result)]) + "\n" + changeset.to_xml() + "\n\n");
	    f.close()
	print result

def help(conn, fnc=None):
    """Prints this help message"""
    import inspect
    self = sys.modules['__main__']
    if fnc:
        try:
            cmd = getattr(self, fnc)
        except:
            cmd = None
        if not inspect.isfunction(cmd):
            print "No function named: %s found" % fnc
            sys.exit(2)
        (args, varargs, varkw, defaults) = inspect.getargspec(cmd)
        print cmd.__doc__
        print "Usage: %s %s" % (fnc, " ".join([ "[%s]" % a for a in args[1:]]))
    else:
        print "Usage: route53zone [command]"
        for cname in dir(self):
            if not cname.startswith("_") and cname != "cmd":
                cmd = getattr(self, cname)
                if inspect.isfunction(cmd):
                    doc = cmd.__doc__
                    print "\t%-20s  %s" % (cname, doc)
    sys.exit(1)


if __name__ == "__main__":
    conn = boto.connect_route53()
    self = sys.modules['__main__']
    if len(sys.argv) >= 2:
        try:
            cmd = getattr(self, sys.argv[1])
        except:
            cmd = None
        args = sys.argv[2:]
    else:
        cmd = help
        args = []
    if not cmd:
        cmd = help
    try:
        cmd(conn, *args)
    except TypeError, e:
        print e
        help(conn, cmd.__name__)
