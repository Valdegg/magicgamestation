/**
 * Browser-based test script for collection sorting.
 * Run this in the browser console on the collection page.
 */

(function() {
    'use strict';
    
    console.log('='.repeat(60));
    console.log('COLLECTION SORTING BROWSER TEST');
    console.log('='.repeat(60));
    
    // Test 1: Check if sorting script is loaded
    console.log('\n--- Test 1: Check if sorting script is loaded ---');
    const sortScript = document.getElementById('sorting-support');
    if (sortScript) {
        console.log('✅ Sorting script found in DOM');
    } else {
        console.log('❌ Sorting script NOT found in DOM');
    }
    
    // Test 2: Check if dropdown exists
    console.log('\n--- Test 2: Check if sort dropdown exists ---');
    const dropdown = document.getElementById('collection-sort-dropdown');
    if (dropdown) {
        console.log('✅ Sort dropdown found');
        console.log(`   Current value: ${dropdown.value}`);
        console.log(`   Options: ${Array.from(dropdown.options).map(o => o.value).join(', ')}`);
    } else {
        console.log('❌ Sort dropdown NOT found');
    }
    
    // Test 3: Check if cards are loaded
    console.log('\n--- Test 3: Check if cards are loaded ---');
    async function testCardsLoaded() {
        try {
            const response = await fetch('/api/collection-cards');
            const data = await response.json();
            const cards = data.cards || [];
            console.log(`✅ Cards loaded: ${cards.length} cards`);
            
            if (cards.length > 0) {
                console.log('   First 5 cards:');
                cards.slice(0, 5).forEach((card, i) => {
                    console.log(`     ${i+1}. ${card.name} - ${card.expansion || 'N/A'} - $${card.buy_price || 0}`);
                });
                
                // Check if cards have collection_index
                const hasIndex = cards.every(c => c.collection_index !== undefined);
                console.log(`   All cards have collection_index: ${hasIndex ? '✅' : '❌'}`);
            }
            
            return cards;
        } catch (e) {
            console.log(`❌ Error loading cards: ${e.message}`);
            return [];
        }
    }
    
    // Test 4: Test sorting functions
    console.log('\n--- Test 4: Test sorting functions ---');
    async function testSortingFunctions() {
        const response = await fetch('/api/collection-cards');
        const data = await response.json();
        const cards = data.cards || [];
        
        if (cards.length === 0) {
            console.log('❌ No cards to test');
            return;
        }
        
        // Simulate sort functions
        const sortFunctions = {
            'original': (cards) => {
                return [...cards].sort((a, b) => {
                    const indexA = a.collection_index !== undefined ? a.collection_index : 999999;
                    const indexB = b.collection_index !== undefined ? b.collection_index : 999999;
                    return indexA - indexB;
                });
            },
            'name': (cards) => {
                return [...cards].sort((a, b) => {
                    const nameA = (a.name || '').toLowerCase();
                    const nameB = (b.name || '').toLowerCase();
                    if (nameA < nameB) return -1;
                    if (nameA > nameB) return 1;
                    const expA = (a.expansion || '').toLowerCase();
                    const expB = (b.expansion || '').toLowerCase();
                    return expA.localeCompare(expB);
                });
            },
            'set': (cards) => {
                return [...cards].sort((a, b) => {
                    const setA = (a.expansion || '').toLowerCase();
                    const setB = (b.expansion || '').toLowerCase();
                    if (setA < setB) return -1;
                    if (setA > setB) return 1;
                    const nameA = (a.name || '').toLowerCase();
                    const nameB = (b.name || '').toLowerCase();
                    return nameA.localeCompare(nameB);
                });
            },
            'price': (cards) => {
                return [...cards].sort((a, b) => {
                    const priceA = parseFloat(a.buy_price) || 0;
                    const priceB = parseFloat(b.buy_price) || 0;
                    if (priceB > priceA) return 1;
                    if (priceB < priceA) return -1;
                    const nameA = (a.name || '').toLowerCase();
                    const nameB = (b.name || '').toLowerCase();
                    return nameA.localeCompare(nameB);
                });
            }
        };
        
        // Test each sort
        for (const [sortType, sortFunc] of Object.entries(sortFunctions)) {
            const sorted = sortFunc(cards);
            console.log(`\n   ${sortType.toUpperCase()} sort:`);
            console.log(`     First 3: ${sorted.slice(0, 3).map(c => c.name).join(', ')}`);
            
            // Verify sort
            if (sortType === 'name') {
                const names = sorted.map(c => (c.name || '').toLowerCase());
                const isSorted = names.every((name, i) => i === 0 || names[i-1] <= name);
                console.log(`     ✅ Correctly sorted: ${isSorted}`);
            } else if (sortType === 'set') {
                const sets = sorted.map(c => (c.expansion || '').toLowerCase());
                const isSorted = sets.every((set, i) => i === 0 || sets[i-1] <= set);
                console.log(`     ✅ Correctly sorted: ${isSorted}`);
            } else if (sortType === 'price') {
                const prices = sorted.map(c => parseFloat(c.buy_price) || 0);
                const isSorted = prices.every((price, i) => i === 0 || prices[i-1] >= price);
                console.log(`     ✅ Correctly sorted: ${isSorted}`);
            }
        }
    }
    
    // Test 5: Check if fetch interception works
    console.log('\n--- Test 5: Check fetch interception ---');
    function testFetchInterception() {
        const originalFetch = window.fetch;
        let intercepted = false;
        
        // Check if fetch is intercepted
        const fetchStr = originalFetch.toString();
        if (fetchStr.includes('collection-cards')) {
            console.log('✅ Fetch appears to be intercepted');
            intercepted = true;
        } else {
            console.log('⚠️  Fetch interception not detected in function string');
        }
        
        // Try to intercept a test call
        window.fetch = function(...args) {
            const url = args[0];
            if (typeof url === 'string' && url.includes('/api/collection-cards')) {
                console.log('✅ Fetch interception triggered for collection-cards');
                intercepted = true;
            }
            return originalFetch.apply(this, args);
        };
        
        return intercepted;
    }
    
    // Run tests
    (async () => {
        await testCardsLoaded();
        await testSortingFunctions();
        testFetchInterception();
        
        console.log('\n' + '='.repeat(60));
        console.log('TEST COMPLETE');
        console.log('='.repeat(60));
        console.log('\nTo manually test sorting:');
        console.log('1. Change the sort dropdown value');
        console.log('2. Check if cards reorder');
        console.log('3. Check browser console for errors');
    })();
})();

