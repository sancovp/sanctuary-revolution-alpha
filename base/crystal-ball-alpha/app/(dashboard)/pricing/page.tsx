import { checkoutAction } from '@/lib/payments/actions';
import { Check, Sparkles } from 'lucide-react';
import { getStripePrices, getStripeProducts } from '@/lib/payments/stripe';
import { SubmitButton } from './submit-button';

// Prices are fresh for one hour max
export const revalidate = 3600;

export default async function PricingPage() {
  const [prices, products] = await Promise.all([
    getStripePrices(),
    getStripeProducts(),
  ]);

  const basePlan = products.find((product) => product.name === 'Explorer') || products.find((product) => product.name === 'Base');
  const plusPlan = products.find((product) => product.name === 'Navigator') || products.find((product) => product.name === 'Plus');

  const basePrice = prices.find((price) => price.productId === basePlan?.id);
  const plusPrice = prices.find((price) => price.productId === plusPlan?.id);

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-300 text-sm mb-4">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Simple, transparent pricing</span>
        </div>
        <h1 className="text-4xl font-bold text-white sm:text-5xl">
          Choose your{' '}
          <span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
            plan
          </span>
        </h1>
        <p className="mt-4 text-gray-400 text-lg max-w-xl mx-auto">
          Start free. Scale as your spaces grow. Every plan includes the full
          Crystal Ball engine — all primitives, all orders, full superposition.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8 max-w-2xl mx-auto">
        <PricingCard
          name={basePlan?.name || 'Explorer'}
          price={basePrice?.unitAmount || 800}
          interval={basePrice?.interval || 'month'}
          trialDays={basePrice?.trialPeriodDays || 7}
          features={[
            'Unlimited Spaces',
            '10,000 API calls / month',
            'Bloom, Scry, Add, Attribute',
            'Full superposition support',
            'Email support',
          ]}
          priceId={basePrice?.id}
        />
        <PricingCard
          name={plusPlan?.name || 'Navigator'}
          price={plusPrice?.unitAmount || 2400}
          interval={plusPrice?.interval || 'month'}
          trialDays={plusPrice?.trialPeriodDays || 7}
          features={[
            'Everything in Explorer',
            'Unlimited API calls',
            '3D visualization dashboard',
            'Priority support + Slack',
            'Early access to subspaces & composability',
          ]}
          priceId={plusPrice?.id}
          highlighted
        />
      </div>
    </main>
  );
}

function PricingCard({
  name,
  price,
  interval,
  trialDays,
  features,
  priceId,
  highlighted = false,
}: {
  name: string;
  price: number;
  interval: string;
  trialDays: number;
  features: string[];
  priceId?: string;
  highlighted?: boolean;
}) {
  return (
    <div
      className={`p-8 rounded-xl border ${highlighted
        ? 'bg-gray-900/80 border-violet-500/40 ring-1 ring-violet-500/20'
        : 'bg-gray-900/40 border-gray-800/50'
        }`}
    >
      <h2 className="text-2xl font-semibold text-white mb-1">{name}</h2>
      <p className="text-sm text-gray-500 mb-6">
        with {trialDays} day free trial
      </p>
      <p className="text-4xl font-bold text-white mb-1">
        ${price / 100}{' '}
        <span className="text-lg font-normal text-gray-500">
          / {interval}
        </span>
      </p>
      <ul className="space-y-3 my-8">
        {features.map((feature, index) => (
          <li key={index} className="flex items-start">
            <Check className="h-5 w-5 text-violet-400 mr-2.5 mt-0.5 flex-shrink-0" />
            <span className="text-gray-300 text-sm">{feature}</span>
          </li>
        ))}
      </ul>
      <form action={checkoutAction}>
        <input type="hidden" name="priceId" value={priceId} />
        <SubmitButton />
      </form>
    </div>
  );
}
