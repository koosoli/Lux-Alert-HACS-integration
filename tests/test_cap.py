"""The CAP parser: the message shape of the feed, odd input, and the documents it must refuse."""
import unittest
from datetime import datetime, timedelta, timezone

from cap_samples import CITY, NOW, cap_xml, info_xml
from custom_components.lu_alert.cap import CapError, parse_cap, parse_time


class ParseTimeTests(unittest.TestCase):
    def test_the_forms_of_iso_8601(self):
        utc = timezone.utc
        self.assertEqual(parse_time("2026-11-02T14:30:00+01:00"), datetime(2026, 11, 2, 13, 30, tzinfo=utc))
        self.assertEqual(parse_time("2026-11-02T14:30:00+0100"), datetime(2026, 11, 2, 13, 30, tzinfo=utc))
        self.assertEqual(parse_time("2026-11-02T14:30:00Z"), datetime(2026, 11, 2, 14, 30, tzinfo=utc))
        self.assertEqual(parse_time("2026-11-02T14:30:00-05:00"), datetime(2026, 11, 2, 19, 30, tzinfo=utc))
        self.assertEqual(parse_time("2026-11-02T14:30:00.250+01:00"), datetime(2026, 11, 2, 13, 30, tzinfo=utc))
        self.assertEqual(parse_time("2026-11-02 14:30"), datetime(2026, 11, 2, 14, 30, tzinfo=utc))

    def test_a_time_without_zone_is_utc_and_python_37_can_read_z(self):
        self.assertEqual(parse_time("2026-11-02T14:30:00").utcoffset(), timedelta(0))

    def test_nonsense_is_none(self):
        for text in (None, "", "yesterday", "2026-13-02T10:00:00Z", "2026-11-02T25:00:00Z", "2026-11-02", "12:00"):
            self.assertIsNone(parse_time(text), text)


class MessageTests(unittest.TestCase):
    def test_a_message_of_the_feed(self):
        [alert] = parse_cap(cap_xml(identifier="LU.1", polygon=CITY, circle=None))
        self.assertEqual(alert.identifier, "LU.1")
        self.assertEqual(alert.sender, "lu-alert@gouvernement.lu")
        self.assertEqual(alert.sent, NOW - timedelta(minutes=30))
        self.assertEqual((alert.status, alert.msg_type, alert.scope), ("Actual", "Alert", "Public"))
        self.assertEqual(alert.codes, ("In-zone",))
        self.assertEqual(len(alert.infos), 6)                         # 3 languages x 2 channels
        english = alert.infos[0]
        self.assertEqual((english.language, english.categories, english.event), ("en-LU", ("Met",), "Wind"))
        self.assertEqual(english.severity, "Severe")
        self.assertEqual(english.expires, NOW + timedelta(hours=2))
        self.assertEqual(english.headline, "Storm warning for the whole country")
        self.assertEqual(english.areas[0].desc, "Luxembourg")
        self.assertEqual(english.areas[0].polygons, (CITY,))
        names = {p.name.rsplit(":", 1)[-1]: p.value for p in english.parameters}
        self.assertEqual(names, {"cb-eu-level": "N2", "canal": "Mobile-App", "canal-id": "1"})

    def test_markup_in_a_description_becomes_plain_text(self):
        [alert] = parse_cap(cap_xml(languages=("en",), channels=("Mobile-App",)))
        self.assertEqual(alert.infos[0].description, "Strong winds expected. Gusts up to 110 km/h.")

    def test_escaped_markup_in_a_description_becomes_plain_text_too(self):
        info = info_xml(description="&lt;p&gt;Water &amp;amp; food&lt;/p&gt;&lt;ul&gt;&lt;li&gt;one&lt;/li&gt;&lt;li&gt;two&lt;/li&gt;&lt;/ul&gt;")
        [alert] = parse_cap(cap_xml(infos=[info]))
        self.assertEqual(alert.infos[0].description, "Water & food one two")

    def test_entities_the_feed_escaped_twice_are_decoded(self):
        # the live feed: a literal &quot; in the text of the description
        info = info_xml(description="Note: The &amp;quot;end date&amp;quot; shows the display period &amp;amp; nothing else.")
        [alert] = parse_cap(cap_xml(infos=[info]))
        self.assertEqual(alert.infos[0].description, 'Note: The "end date" shows the display period & nothing else.')

    def test_a_decoded_angle_bracket_is_not_taken_for_a_tag(self):
        info = info_xml(description="1 &amp;lt; 2 and 3 &amp;gt; 2")
        [alert] = parse_cap(cap_xml(infos=[info]))
        self.assertEqual(alert.infos[0].description, "1 < 2 and 3 > 2")

    def test_markdown_links_of_the_live_feed(self):
        text = ("More information: [www.securite-alimentaire.public.lu/fr/danger/en](https://www.securite-alimentaire.public.lu/fr/danger/en) "
                "and [this page](https://example.lu/a?b=1) or [https://example.lu/](https://example.lu/) [not a link] (x)")
        [alert] = parse_cap(cap_xml(infos=[info_xml(description=text)]))
        self.assertEqual(alert.infos[0].description,
                         "More information: www.securite-alimentaire.public.lu/fr/danger/en and this page (https://example.lu/a?b=1) "
                         "or https://example.lu/ [not a link] (x)")

    def test_a_script_in_a_text_is_just_text(self):
        info = info_xml(headline="<script>alert(1)</script>Danger", description="&lt;script&gt;x()&lt;/script&gt;ok")
        [alert] = parse_cap(cap_xml(infos=[info]))
        self.assertEqual(alert.infos[0].headline, "<script>alert(1)</script>Danger")     # never interpreted
        self.assertNotIn("<", alert.infos[0].description)

    def test_missing_elements_are_empty_not_errors(self):
        [alert] = parse_cap("<alert><identifier>x</identifier><info><headline>h</headline></info></alert>")
        self.assertEqual((alert.sender, alert.status, alert.msg_type, alert.references), ("", "", "", ""))
        self.assertIsNone(alert.sent)
        self.assertEqual(alert.infos[0].areas, ())
        self.assertIsNone(alert.infos[0].expires)

    def test_the_namespace_does_not_matter(self):
        for open_tag in ('<alert xmlns="urn:oasis:names:tc:emergency:cap:1.1">', "<alert>",
                         '<cap:alert xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2">'):
            close = "</cap:alert>" if open_tag.startswith("<cap:") else "</alert>"
            prefix = "cap:" if open_tag.startswith("<cap:") else ""
            xml = "%s<%sidentifier>n</%sidentifier>%s" % (open_tag, prefix, prefix, close)
            self.assertEqual(parse_cap(xml)[0].identifier, "n", open_tag)

    def test_unknown_elements_are_ignored(self):
        [alert] = parse_cap('<alert><identifier>x</identifier><future>1</future><info><x/></info></alert>')
        self.assertEqual(len(alert.infos), 1)

    def test_a_wrapper_with_several_alerts(self):
        xml = "<alerts>%s%s</alerts>" % (cap_xml("a").split("?>", 1)[1], cap_xml("b").split("?>", 1)[1])
        self.assertEqual([a.identifier for a in parse_cap(xml)], ["a", "b"])

    def test_bytes_with_a_bom_and_a_declaration(self):
        data = b"\xef\xbb\xbf" + cap_xml("bom").encode("utf-8")
        self.assertEqual(parse_cap(data)[0].identifier, "bom")

    def test_accents_survive(self):
        [alert] = parse_cap(cap_xml(headline="Alerte tempête à Düdelingen — Gewitter", languages=("fr",),
                                    channels=("Mobile-App",)).encode("utf-8"))
        self.assertEqual(alert.infos[0].headline, "Alerte tempête à Düdelingen — Gewitter")

    def test_references_and_codes_are_kept(self):
        [alert] = parse_cap(cap_xml("u", msg_type="Update", references="s,old,2026-11-02T10:00:00+01:00"))
        self.assertEqual((alert.msg_type, alert.references), ("Update", "s,old,2026-11-02T10:00:00+01:00"))


class RefusedDocumentTests(unittest.TestCase):
    def test_a_document_with_a_doctype_is_refused(self):
        with self.assertRaises(CapError) as ctx:
            parse_cap('<?xml version="1.0"?><!DOCTYPE alert SYSTEM "http://127.0.0.1/x.dtd"><alert/>')
        self.assertIn("DOCTYPE", str(ctx.exception))

    def test_an_entity_bomb_is_refused_before_it_is_parsed(self):
        bomb = ('<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
                '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
                '<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">]>'
                "<alert><identifier>&lol3;</identifier></alert>")
        with self.assertRaises(CapError):
            parse_cap(bomb)
        with self.assertRaises(CapError):
            parse_cap(bomb.encode("utf-8"))

    def test_an_entity_declaration_without_a_doctype_text_is_refused_in_any_case(self):
        with self.assertRaises(CapError):
            parse_cap("<alert><!entity x 'y'></alert>")
        with self.assertRaises(CapError):
            parse_cap("<alert><identifier><!DocType x></identifier></alert>")

    def test_text_that_is_not_xml(self):
        for text in ("", "this is not what you asked for", "<alert><identifier>x</alert>", "{\"json\": true}"):
            with self.assertRaises(CapError, msg=text):
                parse_cap(text)

    def test_xml_that_is_not_cap(self):
        with self.assertRaises(CapError) as ctx:
            parse_cap("<feed><entry/></feed>")
        self.assertIn("feed", str(ctx.exception))

    def test_bytes_that_are_not_utf8(self):
        with self.assertRaises(CapError):
            parse_cap("<alert>é</alert>".encode("latin-1"))


if __name__ == "__main__":
    unittest.main()
