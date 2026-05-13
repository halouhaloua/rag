import { ref, computed } from 'vue';

interface SearchNode {
  id: string;
  name: string;
  category: string;
}

export function useGraphSearch(allNodes: () => SearchNode[]) {
  const searchQuery = ref('');
  const isSearchFocused = ref(false);
  const showSearchResults = ref(false);
  const selectedResultIndex = ref(0);

  const filteredNodes = computed(() => {
    if (!searchQuery.value.trim()) return [];
    const query = searchQuery.value.toLowerCase();
    return allNodes()
      .filter(
        (node) =>
          node.name.toLowerCase().includes(query) ||
          node.category.toLowerCase().includes(query),
      )
      .slice(0, 10);
  });

  function handleSearchInput() {
    showSearchResults.value = true;
    selectedResultIndex.value = 0;
  }

  function handleSearchBlur() {
    setTimeout(() => {
      isSearchFocused.value = false;
      showSearchResults.value = false;
    }, 200);
  }

  function handleSearchClear() {
    searchQuery.value = '';
    showSearchResults.value = false;
    selectedResultIndex.value = 0;
  }

  function navigateResults(direction: number) {
    if (filteredNodes.value.length === 0) return;
    selectedResultIndex.value += direction;
    if (selectedResultIndex.value < 0) {
      selectedResultIndex.value = filteredNodes.value.length - 1;
    } else if (selectedResultIndex.value >= filteredNodes.value.length) {
      selectedResultIndex.value = 0;
    }
  }

  function selectCurrent() {
    if (filteredNodes.value.length === 0) return null;
    return filteredNodes.value[selectedResultIndex.value];
  }

  return {
    searchQuery,
    isSearchFocused,
    showSearchResults,
    selectedResultIndex,
    filteredNodes,
    handleSearchInput,
    handleSearchBlur,
    handleSearchClear,
    navigateResults,
    selectCurrent,
  };
}
