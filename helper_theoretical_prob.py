import numpy as np

def possibilities(phi_sum, s, a, b, p):
    """
    Function that calculates the Lagrange coefficients given the polynomial; also calculates
    and prints the probabilities of correct projection for different combinations of people
    who did not sign, based on the sum of the randomly chosen phases. 

    Args:
        phi_sum : float
        The sum of the randomly chosen phases by QSign and the executives, in {0, π/2, π, 3π/2}.

        s : int
        The y-intercept of the polynomial (f(0)), also referred to as the "secret".
        
        a : int
        The coefficient of the linear term in the polynomial.

        b : int
        The coefficient of the parabolic term in the polynomial.

        p : int
        A prime number included in the definition of the polynomial f(x) = g(x) mod p.
    
    Returns:
        None.
    """
    def lagrange_coefficients():
        
        lag_coeff = []

        # Calculation of lagrange coefficients with interpolation points x = {1, 2, 3}
        for i in [1, 2, 3]:
            c = s + a*i + b*i**2
    
            for j in [val for val in [1, 2, 3] if val!= i]:
                c *= j/(j-i)
            c = c%p
            lag_coeff.append(c)
        
        return lag_coeff

    c1, c2, c3 = lagrange_coefficients()

    # Different combinations of people who did not sign the contract.
    one_person_combos = ['CEO', 'CFO', 'CLO']
    two_person_combos = ['CEO+CFO', 'CEO+CLO', 'CFO+CLO']
    three_person_combos = ['Everyone']
    combinations = {

        # 3 person combinations
        "Everyone": phi_sum + (2*np.pi/p)*(-s),
        # 2 person combinations
        "CEO+CFO": phi_sum + (2*np.pi/p)*(-s + c3),
        "CEO+CLO": phi_sum + (2*np.pi/p)*(-s + c2),
        "CFO+CLO" : phi_sum + (2*np.pi/p)*(-s  + c1),
        # 1 person combinations
        "CEO": phi_sum + (2*np.pi/p)*(-s  + c2 + c3),
        "CFO": phi_sum + (2*np.pi/p)*(-s  + c1 + c3),
        "CLO": phi_sum + (2*np.pi/p)*(-s  + c1 + c2),
    }

    # Calculation of the correct projection probability based on the sum of randomly chosen phases.    
    def prob(phi_sum, chi):

        if phi_sum==0:
            return np.cos(chi/2)**2
        elif phi_sum==np.pi/2:
            return 0.5*(1 + np.sin(chi))
        elif phi_sum==np.pi:
            return np.sin(chi/2)**2
        elif phi_sum==1.5*np.pi:
            return 0.5*(1 - np.sin(chi))
        else:
            raise ValueError("Sum of randomly chosen angles is not in {0, π/2, π, 3π/2}")
    
    # Printing the final results.
    print('\n')
    print(f"{'='*30} Possible Scenarios {'='*30}")
    print(f"{'-'*30} 1-Person Scenarios {'-'*30}")
    for scenario in one_person_combos:
        print(f"Didn't sign: {scenario}, Probability ≈ {100*prob(phi_sum, combinations[scenario]):.1f}%")
    print(f"{'-'*30} 2-Person Scenarios {'-'*30}")
    for scenario in two_person_combos:
        print(f"Didn't sign: {scenario}, Probability ≈ {100*prob(phi_sum, combinations[scenario]):.1f}%")
    print(f"{'-'*30} 3-Person Scenarios {'-'*30}")
    for scenario in three_person_combos:
        print(f"Didn't sign: {scenario}, Probability ≈ {100*prob(phi_sum, combinations[scenario]):.1f}%")
    print(f"{'='*80}")
    



        
        