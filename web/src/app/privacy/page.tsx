import type { Metadata } from 'next';
import { RULES } from '@/lib/rules';

export const metadata: Metadata = {
  title: 'Privacy — DALOY Scan',
  description: 'Walang server, walang lokasyon, walang account. Nasa telepono lang ang lahat.',
};

/**
 * Server-rendered so the privacy claims are part of the shipped HTML and can be read
 * without executing anything. Verification counts come from the compiled bundle, so
 * the page cannot drift from what the app actually knows.
 */
export default function PrivacyPage() {
  const { legal_sources_verified: verified, legal_sources_total: total } = RULES.verification;

  return (
    <section>
      <h2>Privacy at tungkol sa app</h2>

      <h3>Ano ang kinokolekta namin</h3>
      <p>
        <strong>Wala.</strong> Walang server ang bersyong ito. Ang barangay na pinili ninyo at
        ang Bote Bank ninyo ay nasa telepono lang ninyo, at mabubura kapag binura ninyo ang
        data ng browser.
      </p>

      <h3>Bakit hindi hinihingi ang lokasyon</h3>
      <p>
        Personal na impormasyon ang eksaktong lokasyon sa ilalim ng <strong>RA 10173</strong>{' '}
        at ng <strong>Cainta Ordinance 2023-005</strong>. Ang scan na ginawa sa bahay ninyo ay
        address ninyo. Kaya barangay lang ang itinatanong — at kahit iyon ay hindi umaalis sa
        telepono ninyo.
      </p>

      <h3>Tungkol sa mga presyo</h3>
      <p>
        Ang mga presyong ipinapakita ay <strong>tinatayang halaga lamang</strong>, hindi pa
        nabe-verify sa alinmang junkshop sa Cainta. Nagbabago ang totoong presyo araw-araw at
        bawat tindahan. <strong>Magtanong pa rin sa junkshop.</strong> Wala kaming kinikita sa
        anumang transaksyon ninyo.
      </p>

      <h3>Tungkol sa mga ordinansa</h3>
      <p>
        Ang mga ordinansang binabanggit ay galing sa planning document ng proyekto, at{' '}
        {verified} sa {total} ang nabe-verify sa orihinal na dokumento. Kaya hindi namin
        sinasabing opisyal na pahayag ito ng Pamahalaang Bayan ng Cainta. Kung may pagkakaiba,
        ang opisyal na dokumento ng Bayan ang masusunod.
      </p>

      <h3>Ang daloy ng tubig</h3>
      <p>
        Ang ipinapakitang daloy ay <strong>schematic</strong> — isang dayagram ng
        pangkalahatang direksyon, hindi mapa. Hindi pa namin nave-verify kung aling sapa ang
        dumadaloy mula sa bawat barangay, kaya wala kaming pinapangalanang sapa.
      </p>

      <h3>Ang mga karapatan ninyo sa ilalim ng RA 10173</h3>
      <p>
        Dahil walang datos na umaalis sa telepono ninyo, kayo mismo ang may hawak ng lahat.
        Mabubura ninyo ang lahat sa pamamagitan ng pagbura ng data ng browser para sa site na
        ito. Kung magkaroon man kami ng server sa hinaharap, babaguhin muna ang paunawang ito
        bago iyon mangyari.
      </p>

      <h3>English summary</h3>
      <p>
        This version has no server. Your barangay and your Bote Bank ledger stay on your
        phone. No precise location is ever requested — the app makes no geolocation call at
        all. Prices are unverified estimates; always confirm at the shop. Ordinance guidance
        is not yet verified against the source documents and is therefore not attributed to
        the municipality. The water flow shown is a schematic diagram, not surveyed geometry.
      </p>
    </section>
  );
}
