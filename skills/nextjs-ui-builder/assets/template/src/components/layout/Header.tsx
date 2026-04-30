import Link from 'next/link';

export function Header() {
  return (
    <header className="bg-white shadow">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <Link href="/" className="text-xl font-bold text-gray-900">
          MyApp
        </Link>
        <nav className="flex items-center gap-4">
          <Link href="/" className="text-gray-600 hover:text-gray-900">
            Home
          </Link>
        </nav>
      </div>
    </header>
  );
}
