#!/usr/bin/env node

/**
 * Component Generator Script
 * Creates new React/Next.js components with proper structure and files
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function kebabToPascalCase(str) {
  return str
    .split('-')
    .map(capitalize)
    .join('');
}

function createDirectory(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    console.log(`✅ Created directory: ${dirPath}`);
  }
}

function createComponent(componentName, componentType, options = {}) {
  const {
    withStyles = false,
    withTests = false,
    withStories = false,
    exportType = 'default'
  } = options;

  const pascalCaseName = kebabToPascalCase(componentName);
  const kebabCaseName = componentName.toLowerCase();

  // Determine component directory based on type
  let componentDir;
  switch (componentType) {
    case 'ui':
      componentDir = path.join(process.cwd(), 'components', 'ui');
      break;
    case 'dashboard':
      componentDir = path.join(process.cwd(), 'components', 'dashboard');
      break;
    case 'chat':
      componentDir = path.join(process.cwd(), 'components', 'chat');
      break;
    case 'layout':
      componentDir = path.join(process.cwd(), 'components', 'layout');
      break;
    default:
      componentDir = path.join(process.cwd(), 'components', componentName);
  }

  createDirectory(componentDir);

  // JSX component content
  const jsxContent = `import React from 'react';
${withStyles ? `import styles from './${pascalCaseName}.module.css';\n` : ''}

const ${pascalCaseName} = ({ children, className = '', ...props }) => {
  return (
    <div
      className={\`\${styles.${kebabCaseName} \${className}\`.trim()}
      {...props}
    >
      {children}
    </div>
  );
};

export ${exportType === 'default' ? 'default' : `const ${pascalCaseName} =`} ${pascalCaseName};
`;

  // TypeScript version
  const tsContent = `import React from 'react';

interface ${pascalCaseName}Props {
  children?: React.ReactNode;
  className?: string;
  [key: string]: any;
}

const ${pascalCaseName}: React.FC<${pascalCaseName}Props> = ({
  children,
  className = '',
  ...props
}) => {
  return (
    <div
      className={\`\${className}\`.trim()}
      {...props}
    >
      {children}
    </div>
  );
};

export ${exportType === 'default' ? 'default' : `const ${pascalCaseName} =`} ${pascalCaseName};
`;

  // CSS Module content
  const cssContent = `.${kebabCaseName} {
  /* Add your styles here */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  border-radius: 0.5rem;
  background-color: #ffffff;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

@media (max-width: 768px) {
  .${kebabCaseName} {
    padding: 0.5rem;
  }
}
`;

  // Test file content
  const testContent = `import React from 'react';
import { render, screen } from '@testing-library/react';
import ${pascalCaseName} from './${pascalCaseName}';

describe('${pascalCaseName}', () => {
  it('renders children correctly', () => {
    render(
      <${pascalCaseName}>
        <span>Test Child</span>
      </${pascalCaseName}>
    );

    expect(screen.getByText('Test Child')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <${pascalCaseName} className="custom-class">
        Test
      </${pascalCaseName}>
    );

    const element = screen.getByText('Test');
    expect(element).toHaveClass('custom-class');
  });
});
`;

  // Storybook story
  const storyContent = `import React from 'react';
import { ComponentStory, ComponentMeta } from '@storybook/react';

import ${pascalCaseName} from './${pascalCaseName}';

export default {
  title: '${componentType ? capitalize(componentType) + '/' : ''}${pascalCaseName}',
  component: ${pascalCaseName},
  argTypes: {},
} as ComponentMeta<typeof ${pascalCaseName}>;

const Template: ComponentStory<typeof ${pascalCaseName}> = (args) => <${pascalCaseName} {...args} />;

export const Default = Template.bind({});
Default.args = {
  children: 'Hello, ${pascalCaseName}!',
};
`;

  // Write files
  const componentPath = path.join(componentDir, `${pascalCaseName}.jsx`);
  fs.writeFileSync(componentPath, jsxContent);
  console.log(`✅ Created component: ${componentPath}`);

  if (withStyles) {
    const cssPath = path.join(componentDir, `${pascalCaseName}.module.css`);
    fs.writeFileSync(cssPath, cssContent);
    console.log(`✅ Created styles: ${cssPath}`);
  }

  if (withTests) {
    const testPath = path.join(componentDir, `${pascalCaseName}.test.js`);
    fs.writeFileSync(testPath, testContent);
    console.log(`✅ Created test: ${testPath}`);
  }

  if (withStories) {
    const storyPath = path.join(componentDir, `${pascalCaseName}.stories.js`);
    fs.writeFileSync(storyPath, storyContent);
    console.log(`✅ Created story: ${storyPath}`);
  }

  // Create index file for easy imports
  const indexPath = path.join(componentDir, 'index.js');
  if (!fs.existsSync(indexPath)) {
    const indexContent = `export { default as ${pascalCaseName} } from './${pascalCaseName}';\n`;
    fs.writeFileSync(indexPath, indexContent);
    console.log(`✅ Created index: ${indexPath}`);
  } else {
    // Append to existing index file
    const currentIndex = fs.readFileSync(indexPath, 'utf8');
    if (!currentIndex.includes(pascalCaseName)) {
      const newIndexContent = `export { default as ${pascalCaseName} } from './${pascalCaseName};\n${currentIndex}`;
      fs.writeFileSync(indexPath, newIndexContent);
      console.log(`✅ Updated index: ${indexPath}`);
    }
  }
}

function showHelp() {
  console.log(`
Usage: node create-component.js [options] <component-name>

Options:
  -t, --type <type>      Component type (ui, dashboard, chat, layout) [default: generic]
  --with-styles          Create CSS module file
  --with-tests           Create test file
  --with-stories         Create Storybook story
  --named-export         Create named export instead of default export
  -h, --help            Show help

Examples:
  node create-component.js Button --with-styles --with-tests
  node create-component.js ChatInterface --type chat --with-stories
  node create-component.js DashboardCard --type dashboard --named-export
  `);
}

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {};
  const positional = [];

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--help' || arg === '-h') {
      showHelp();
      process.exit(0);
    } else if (arg === '--with-styles') {
      options.withStyles = true;
    } else if (arg === '--with-tests') {
      options.withTests = true;
    } else if (arg === '--with-stories') {
      options.withStories = true;
    } else if (arg === '--named-export') {
      options.exportType = 'named';
    } else if (arg === '--type' || arg === '-t') {
      options.componentType = args[++i];
    } else if (arg.startsWith('-')) {
      console.error(`Unknown option: ${arg}`);
      showHelp();
      process.exit(1);
    } else {
      positional.push(arg);
    }
  }

  if (positional.length === 0) {
    console.error('Error: Component name is required');
    showHelp();
    process.exit(1);
  }

  return {
    componentName: positional[0],
    options: {
      componentType: options.componentType || 'generic',
      withStyles: options.withStyles || false,
      withTests: options.withTests || false,
      withStories: options.withStories || false,
      exportType: options.exportType || 'default'
    }
  };
}

// Main execution
try {
  const { componentName, options } = parseArgs();
  console.log(`🚀 Creating component: ${componentName}`);
  createComponent(componentName, options.componentType, options);
  console.log(`\n✨ Component ${componentName} created successfully!`);
} catch (error) {
  console.error(`❌ Error creating component: ${error.message}`);
  process.exit(1);
}