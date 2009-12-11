;---------------------------------------------
; workspace-structure.update_strengths
;---------------------------------------------

;---------------------------------------------
; description.calculate-internal-strength
;---------------------------------------------

;---------------------------------------------
; description.calculate-external-strength
;---------------------------------------------

;---------------------------------------------
; bond.calculate-internal-strength
; bond.calculate-external-strength
;---------------------------------------------

;---------------------------------------------
; group.calculate-internal-strength
;---------------------------------------------
    
;---------------------------------------------
; group.calculate-external-strength
;---------------------------------------------

(defmethod (correspondence :calculate-internal-strength) 
		(&aux relevant-distinguishing-cms 
		     average-strength internal-coherence-factor
		     num-of-concept-mappings-factor num-of-concept-mappings)
; a function of how many concept-mappings there are, how strong they are,
; and how much internal coherence there is among concept mappings.
  (setq relevant-distinguishing-cms
	(send self :relevant-distinguishing-cms))

  (if* (null relevant-distinguishing-cms)
   then 0
   else (setq average-strength
	      (list-average 
		  (send-method-to-list 
		      relevant-distinguishing-cms :strength)))

        (setq num-of-concept-mappings (length relevant-distinguishing-cms))
        (setq num-of-concept-mappings-factor
	      (case num-of-concept-mappings
		    (1 .8)  
		    (2 1.2)
		    (t 1.6)))

        (if* (send self :internally-coherent?)
         then (setq internal-coherence-factor 2.5)
         else (setq internal-coherence-factor 1))

        (min 100 (round (* average-strength internal-coherence-factor
			   num-of-concept-mappings-factor)))))

;---------------------------------------------

(defmethod (correspondence :calculate-external-strength) ()
  (send self :support))

;---------------------------------------------

(defmethod (correspondence :internally-coherent?) 
           (&aux cm-list result)
; for now this returns t if there is any pair of relevant-distinguishing 
; concept-mappings that support each other.  this isn't quite right.
  (setq cm-list
	(send self :relevant-distinguishing-cms))
  (if* (> (length cm-list) 1)
   then (loop for cm in cm-list until result do
	      (loop for other-cm in (remove cm cm-list) 
	            when (supporting-concept-mappings? cm other-cm)
	            return (setq result t))))
  result)
	      
;---------------------------------------------
; rule.calculate-internal-strength
;---------------------------------------------

;---------------------------------------------
; rule.calculate-external-strength
;---------------------------------------------

;---------------------------------------------
; workspace-structure.calculate-total-strength
;---------------------------------------------

;---------------------------------------------
; workspace-structure.total-weakness
;---------------------------------------------

;---------------------------------------------
; concept-mapping.slippability
;---------------------------------------------

(defun supporting-correspondences? (c1 c2 &aux (result nil))
; returns t if c1 supports c2, nil otherwise.  for now, c1 is 
; defined to support c2 if c1 is not incompatible with c2, and 
; has a concept-mapping that supports the concept-mappings of c2.

  (cond ((or (eq (send c1 :obj1) (send c2 :obj1))	
	     (eq (send c1 :obj2) (send c2 :obj2)))
         (setq result nil))
	((incompatible-correspondences? c1 c2) (setq result nil))
        (t (loop for cm1 in (send c1 :distinguishing-concept-mappings) 
		 until result do
                  (loop for cm2 in (send c2 :distinguishing-concept-mappings)
		        when (supporting-concept-mappings? cm1 cm2) 
			do (setq result t)
			   (return)))))
  result)

;---------------------------------------------

(defun incompatible-correspondences? (c1 c2 &aux (result nil))
; returns t if c1 is incompatible with c2, nil otherwise.  for now, c1 is 
; defined to be incompatible with c2 if c1 and c2 share objects, or c1 has a 
; concept-mapping incompatible with the concept-mappings of c2.


  (if* (or (eq (send c1 :obj1) (send c2 :obj1))	
	  (eq (send c1 :obj2) (send c2 :obj2)))
   then (setq result t)
   else (loop for cm1 in (send c1 :concept-mapping-list) until result do
              (loop for cm2 in (send c2 :concept-mapping-list) 
		    when (incompatible-concept-mappings? cm1 cm2) do
                         (setq result t)
			 (return))))
  result)

;---------------------------------------------
; supporting-concept-mappings? | Mapping.is_supporting_concept_mapping
;---------------------------------------------

;---------------------------------------------
; incompatible-concept-mappings? | Mapping.is_incompatible_concept_mapping
; incompatible-concept-mapping-lists?
;---------------------------------------------

;---------------------------------------------
; related? | slipnode.are_related
;---------------------------------------------

;---------------------------------------------
; linked? | slipnode.are_linked
;---------------------------------------------

;---------------------------------------------
; slip-linked? | slipnode.are_slip_linked
;---------------------------------------------

;---------------------------------------------
; slipnode.bond-degree-of-association | slipnode.bond_degree_of_association
;---------------------------------------------

;---------------------------------------------
; bond.importance
;---------------------------------------------

;---------------------------------------------
; bond.happiness
; bond.unhappiness
;---------------------------------------------

;---------------------------------------------
; bond.salience
;---------------------------------------------

;---------------------------------------------
; slipnode.local-descriptor-support | slipnode.local_descriptor_support
;---------------------------------------------
  
;---------------------------------------------
; slipnode.local-description-type-support | slipnode.local_description_type_support
;---------------------------------------------

;---------------------------------------------
; slipnode.total-description-type-support | slipnode.total_desription_type_support
;---------------------------------------------

;---------------------------------------------
; description.local-support
;---------------------------------------------

;---------------------------------------------
; bond.number-of-local-supporting-bonds
;---------------------------------------------
  (setq num-of-supporting-bonds 
	(loop for other-bond in (remove self (send string :bond-list)) 
	      when (and (not (= (letter-distance 
				    (send self :left-obj)
		                    (send other-bond :left-obj)) 0))
                        (not (= (letter-distance 
				    (send self :right-obj)
			            (send other-bond :right-obj)) 0))
		        (eq (send other-bond :bond-category) 
			    bond-category)
		        (eq (send other-bond :direction-category) 
			    direction-category))
	      count t into supporting-bond-count
	      finally (return supporting-bond-count)))

  num-of-supporting-bonds)

;---------------------------------------------
; bond.local-density
;---------------------------------------------

;---------------------------------------------
; bond.local-support
;---------------------------------------------

;---------------------------------------------
; group.number-of-local-supporting-groups
;---------------------------------------------

;---------------------------------------------
; group.local-density
;---------------------------------------------

;---------------------------------------------
; group.local-support
;---------------------------------------------
	   
;---------------------------------------------
; correspondence.support | Correspondence.support
;---------------------------------------------

;---------------------------------------------
; local-bond-category-relevance
;---------------------------------------------

;---------------------------------------------
; local-direction-category-relevance
;---------------------------------------------

;---------------------------------------------
; recursive-group-member? | Gropu.is_recursive_member
;---------------------------------------------
