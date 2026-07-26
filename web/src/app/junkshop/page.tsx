import { RULES } from '@/lib/rules';

/**
 * Zero surveyed shops (plan Phase 2).
 *
 * An empty map with a "no results" toast would imply there are no junkshops in
 * Cainta, which is false — there are many. The data simply does not exist yet, and
 * saying so is both more honest and more useful than an empty pin layer.
 *
 * Server component: the count is a build-time fact from the bundle.
 */
export default function JunkshopPage() {
  const { verified_shops: verified } = RULES.verification;

  return (
    <section>
      <h2>Mga junkshop</h2>

      {verified > 0 ? (
        <p>{verified} na-verify na junkshop.</p>
      ) : (
        <>
          <div className="empty">
            <strong>Wala pa kaming listahan.</strong>
            <div>
              Hindi ito nangangahulugang walang junkshop sa Cainta — marami. Ang ibig sabihin,
              hindi pa namin nabibisita at nave-verify ang mga ito, at ayaw naming magpadala
              kayo sa isang tindahang sarado na o hindi tumatanggap ng dala ninyo.
            </div>
          </div>

          <p className="fineprint">
            Sa susunod na bahagi ng proyekto, bibisitahin ang 30–60 junkshop sa Cainta para
            itala ang lokasyon, presyo, at kung ano ang tinatanggap nila.
          </p>
        </>
      )}
    </section>
  );
}
