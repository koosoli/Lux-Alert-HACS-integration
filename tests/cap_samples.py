"""Builders for CAP-LU messages in the shape of the LU-Alert feed (one <info> per language and channel).

Shared with the Domoticz-LUAlert plugin. The shape follows the CAP-LU 1.1 profile and what that plugin saw in the live
feed on 2026-11-04 (levels ALERT_LVL_1 ... ALERT_LVL_4 and TEST, references like ``[ALVA],id,sent``).
"""
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

NOW = datetime(2026, 11, 2, 12, 0, 0, tzinfo=timezone.utc)
LEVEL_PARAM = "urn:oasis:names:tc:emergency:cap:1.2:profile:cap-lu:1.0:cb-eu-level"

# Luxembourg City (49.6116 N, 6.1319 E) is inside CITY, Esch-sur-Alzette (49.4958 N, 5.9806 E) inside ESCH
CITY = "49.58,6.08 49.58,6.19 49.64,6.19 49.64,6.08 49.58,6.08"
ESCH = "49.46,5.93 49.46,6.03 49.53,6.03 49.53,5.93 49.46,5.93"
HOME = (49.6116, 6.1319)

HEADLINES = {
    "en": "Storm warning for the whole country",
    "de": "Sturmwarnung für das ganze Land",
    "fr": "Alerte tempête pour tout le pays",
}


def iso(moment):
    return moment.astimezone(timezone(timedelta(hours=1))).strftime("%Y-%m-%dT%H:%M:%S+01:00")


def info_xml(language="en", channel="Mobile-App", channel_id=1, level="N2", severity="Severe", headline=None,
             description="<p>Strong winds expected.</p><p>Gusts up to <b>110 km/h</b>.</p>",
             instruction="Stay indoors.", expires=None, area_desc="Luxembourg", polygon=None, circle=None,
             categories=("Met",), event="Wind", effective=None, with_level=True):
    headline = HEADLINES.get(language, "Headline") if headline is None else headline
    parts = ["<info>", "<language>%s-LU</language>" % language]
    parts += ["<category>%s</category>" % c for c in categories]
    parts += ["<event>%s</event>" % escape(event), "<urgency>Immediate</urgency>",
              "<severity>%s</severity>" % severity, "<certainty>Likely</certainty>"]
    if effective:
        parts.append("<effective>%s</effective>" % iso(effective))
    if expires:
        parts.append("<expires>%s</expires>" % iso(expires))
    parts += ["<senderName>Gouvernement du Grand-Duché de Luxembourg</senderName>",
              "<headline>%s</headline>" % escape(headline),
              "<description>%s</description>" % description,
              "<instruction>%s</instruction>" % escape(instruction),
              "<web>https://lu-alert.lu/</web>"]
    if with_level:
        parts.append("<parameter><valueName>%s</valueName><value>%s</value></parameter>" % (LEVEL_PARAM, level))
    parts.append("<parameter><valueName>canal</valueName><value>%s</value></parameter>" % channel)
    parts.append("<parameter><valueName>canal-id</valueName><value>%d</value></parameter>" % channel_id)
    parts.append("<area><areaDesc>%s</areaDesc>" % escape(area_desc))
    if polygon:
        parts.append("<polygon>%s</polygon>" % polygon)
    if circle:
        parts.append("<circle>%s</circle>" % circle)
    parts.append("</area></info>")
    return "".join(parts)


def cap_xml(identifier="LU.2026.0001", sent=None, msg_type="Alert", status="Actual", references=None, infos=None,
            level="N2", severity="Severe", expires="default", polygon=None, languages=("en", "de", "fr"),
            channels=("Mobile-App", "Siren"), **info_kw):
    """One CAP message. ``expires="default"``: two hours after NOW; ``None``: no end time. The same text for the
    channels of a language; the siren block has no headline, as in the real profile."""
    sent = sent or NOW - timedelta(minutes=30)
    if expires == "default":
        expires = NOW + timedelta(hours=2)
    if infos is None:
        infos = []
        channel_id = 0
        for language in languages:
            for channel in channels:
                channel_id += 1
                kw = dict(info_kw)
                if channel == "Siren":
                    kw.update(headline="", description="", instruction="")
                infos.append(info_xml(language, channel, channel_id, level=level, severity=severity, expires=expires,
                                      polygon=polygon, **kw))
    head = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            "<alert xmlns=\"urn:oasis:names:tc:emergency:cap:1.2\">",
            "<identifier>%s</identifier>" % identifier, "<sender>lu-alert@gouvernement.lu</sender>",
            "<sent>%s</sent>" % iso(sent), "<status>%s</status>" % status, "<msgType>%s</msgType>" % msg_type,
            "<scope>Public</scope>", "<code>In-zone</code>"]
    if references:
        head.append("<references>%s</references>" % references)
    return "".join(head + list(infos) + ["</alert>"])


def reference(identifier, sent):
    return "lu-alert@gouvernement.lu,%s,%s" % (identifier, iso(sent))
