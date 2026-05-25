import { useCallback, useEffect, useState } from "react";
import { BrowserProvider, formatEther, JsonRpcSigner } from "ethers";
import { toast } from "sonner";

const MANTLE_MAINNET_CHAIN_ID = "0x1388"; // 5000 in hex
const MANTLE_MAINNET_RPC = "https://rpc.mantle.xyz";
const MNT_SYMBOL = "MNT";

export type WalletState = {
  connected: boolean;
  address: string | null;
  chainId: string | null;
  balance: string | null;
  signer: JsonRpcSigner | null;
  isMantle: boolean;
};

declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
      on: (event: string, handler: (...args: unknown[]) => void) => void;
      removeListener: (event: string, handler: (...args: unknown[]) => void) => void;
    };
  }
}

export function useWallet() {
  const [state, setState] = useState<WalletState>({
    connected: false,
    address: null,
    chainId: null,
    balance: null,
    signer: null,
    isMantle: false,
  });

  const updateState = useCallback(async (provider: BrowserProvider, accounts: string[]) => {
    try {
      const signer = await provider.getSigner();
      const network = await provider.getNetwork();
      const chainId = "0x" + network.chainId.toString(16).toUpperCase();
      const balanceWei = await provider.getBalance(accounts[0]);
      const balance = Number(formatEther(balanceWei)).toFixed(4);
      setState({
        connected: true,
        address: accounts[0],
        chainId,
        balance,
        signer,
        isMantle: chainId === MANTLE_MAINNET_CHAIN_ID,
      });
    } catch {
      setState((prev) => ({ ...prev, connected: false }));
      toast.error("Wallet state could not be refreshed.");
    }
  }, []);

  const connect = useCallback(async () => {
    if (!window.ethereum) {
      toast.error("No Web3 wallet detected. Install MetaMask or a compatible wallet.");
      return;
    }
    try {
      const accounts = (await window.ethereum.request({ method: "eth_requestAccounts" })) as string[];
      const provider = new BrowserProvider(window.ethereum);
      await updateState(provider, accounts);
      toast.success("Wallet connected.");
    } catch (e) {
      console.error("Wallet connection failed:", e);
      toast.error("Wallet connection was rejected or failed.");
    }
  }, [updateState]);

  const switchToMantle = useCallback(async () => {
    if (!window.ethereum) return;
    try {
      await window.ethereum.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: MANTLE_MAINNET_CHAIN_ID }],
      });
      toast.success("Switched to Mantle Mainnet.");
    } catch (e: unknown) {
      const err = e as { code?: number };
      if (err.code === 4902) {
        try {
          await window.ethereum.request({
            method: "wallet_addEthereumChain",
            params: [
              {
                chainId: MANTLE_MAINNET_CHAIN_ID,
                chainName: "Mantle Mainnet",
                rpcUrls: [MANTLE_MAINNET_RPC],
                nativeCurrency: { name: "MNT", symbol: MNT_SYMBOL, decimals: 18 },
                blockExplorerUrls: ["https://explorer.mantle.xyz/"],
              },
            ],
          });
          toast.success("Mantle Mainnet added to wallet.");
        } catch (addErr) {
          console.error("Failed to add Mantle network:", addErr);
          toast.error("Could not add Mantle Mainnet to the wallet.");
        }
      } else {
        console.error("Failed to switch network:", e);
        toast.error("Could not switch to Mantle Mainnet.");
      }
    }
  }, []);

  const signMessage = useCallback(
    async (message: string): Promise<string | null> => {
      if (!state.signer) return null;
      try {
        const signature = await state.signer.signMessage(message);
        toast.success("Attestation signature captured.");
        return signature;
      } catch (e) {
        console.error("Sign message failed:", e);
        toast.error("Signature request was rejected.");
        return null;
      }
    },
    [state.signer],
  );

  useEffect(() => {
    if (!window.ethereum) return;
    const onAccountsChanged = (...args: unknown[]) => {
      const accounts = args[0] as string[];
      if (accounts.length === 0) {
        setState({
          connected: false,
          address: null,
          chainId: null,
          balance: null,
          signer: null,
          isMantle: false,
        });
      } else {
        const provider = new BrowserProvider(window.ethereum!);
        updateState(provider, accounts);
      }
    };
    const onChainChanged = () => {
      // Force a refresh when chain changes
      window.location.reload();
    };

    window.ethereum.on("accountsChanged", onAccountsChanged);
    window.ethereum.on("chainChanged", onChainChanged);

    return () => {
      window.ethereum?.removeListener("accountsChanged", onAccountsChanged);
      window.ethereum?.removeListener("chainChanged", onChainChanged);
    };
  }, [updateState]);

  return { ...state, connect, switchToMantle, signMessage };
}
