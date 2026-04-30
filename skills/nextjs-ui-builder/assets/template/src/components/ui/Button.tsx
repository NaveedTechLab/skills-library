interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  loading?: boolean;
}

export function Button({
  children,
  variant = 'primary',
  loading = false,
  disabled,
  className = '',
  ...props
}: ButtonProps) {
  const baseStyles = 'px-4 py-2 rounded font-medium transition-colors';
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  };

  return (
    <button
      disabled={disabled || loading}
      className={`${baseStyles} ${variants[variant]} ${
        disabled || loading ? 'opacity-50 cursor-not-allowed' : ''
      } ${className}`}
      {...props}
    >
      {loading ? 'Loading...' : children}
    </button>
  );
}
