/**
 * Test script to load images exactly as the frontend does
 * Run with: node test_image_loading.js
 */

// Simulate the normalizeCardName function from cardDatabase.ts
function normalizeCardName(name) {
  return name
    .replace(/[',]/g, '') // Remove apostrophes and commas  
    .replace(/[^a-zA-Z0-9]/g, '_') // Replace non-alphanumeric with underscore
    .replace(/_+/g, '_') // Collapse multiple underscores
    .replace(/^_|_$/g, ''); // Trim leading/trailing underscores
}

// Simulate the getCardImagePaths function
function getCardImagePaths(cardName, setCode) {
  const normalized = normalizeCardName(cardName);
  const paths = [];
  
  // Try with set code first (if provided)
  if (setCode) {
    paths.push(`/card_images/${normalized}_${setCode}.jpg`);
    paths.push(`/card_images/${normalized}_${setCode}.png`);
  }
  
  // Try without set code
  paths.push(`/card_images/${normalized}.jpg`);
  paths.push(`/card_images/${normalized}.png`);
  
  // Fallback to card back
  paths.push('/cards/card-back.jpg');
  
  return paths;
}

// Test loading images exactly as Card.tsx does
async function testImageLoading(cardName, setCode) {
  console.log(`\n🧪 Testing image loading for: "${cardName}"${setCode ? ` (set: ${setCode})` : ''}`);
  
  const possiblePaths = getCardImagePaths(cardName, setCode);
  console.log('📁 Generated paths:', possiblePaths);
  
  for (const path of possiblePaths) {
    try {
      console.log(`  🔍 Trying: ${path}`);
      
      // Create a full URL (simulating browser behavior)
      const fullUrl = `http://localhost:5173${path}`;
      console.log(`  🌐 Full URL: ${fullUrl}`);
      
      // Try to load the image
      const img = new Image();
      const loaded = await new Promise((resolve) => {
        img.onload = () => {
          console.log(`  ✅ SUCCESS: ${path}`);
          resolve(true);
        };
        img.onerror = () => {
          console.log(`  ❌ FAILED: ${path}`);
          resolve(false);
        };
        img.src = path; // Use relative path as browser does
      });
      
      if (loaded) {
        console.log(`  ✅ Image loaded successfully!`);
        return path;
      }
    } catch (e) {
      console.log(`  ⚠️ Error: ${path}`, e.message);
      continue;
    }
  }
  
  console.log(`  ⚠️ All paths failed`);
  return null;
}

// Test cases
async function runTests() {
  console.log('='.repeat(60));
  console.log('IMAGE LOADING TEST - Simulating Frontend Behavior');
  console.log('='.repeat(60));
  
  // Test cases from the user's issue
  await testImageLoading('Roar of the Wurm', 'ODY');
  await testImageLoading('Basking Rootwalla');
  await testImageLoading('Lightning Bolt');
  await testImageLoading('Island');
  
  console.log('\n' + '='.repeat(60));
  console.log('Test complete!');
  console.log('='.repeat(60));
  console.log('\nNote: This test runs in Node.js and may not perfectly');
  console.log('simulate browser behavior. Check browser console for');
  console.log('actual frontend loading behavior.');
}

// Run tests
runTests().catch(console.error);

